package leeashmore.investikid.ai.app

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.spec.MGF1ParameterSpec
import javax.crypto.Cipher
import javax.crypto.spec.OAEPParameterSpec
import javax.crypto.spec.PSource

/**
 * Biometric-bound secure storage (SP-Bio H1) — Android parity with the iOS
 * BiometricVault. Each secret is encrypted with the PUBLIC half of an RSA
 * keypair held in the AndroidKeyStore (so `set` never prompts), and decrypted
 * with the PRIVATE half, which requires biometric authentication and is created
 * with `setInvalidatedByBiometricEnrollment(true)`. Enrolling a new fingerprint
 * / face permanently invalidates the private key: `Cipher.init(DECRYPT)` then
 * throws `KeyPermanentlyInvalidatedException`, which we surface as "gone" (empty
 * resolve) so the app forgets the credential and falls back to password.
 *
 * Contract (mirrors ios/App/App/BiometricVaultPlugin.swift and
 * src/lib/biometricVault.ts):
 *   get() resolves { value } on a biometric match, {} when absent/invalidated,
 *   and REJECTS on user-cancel / auth-failure.
 */
@CapacitorPlugin(name = "BiometricVault")
class BiometricVaultPlugin : Plugin() {

    private val keystoreName = "AndroidKeyStore"
    private val prefsName = "biometric_vault"
    private val transformation = "RSA/ECB/OAEPwithSHA-256andMGF1Padding"

    // AndroidKeyStore's OAEP forces MGF1 to use SHA-1 even when the content digest
    // is SHA-256; without an explicit spec, encrypt (SHA-1 MGF1 default) and the
    // keystore decrypt disagree and doFinal throws. Pin MGF1 to SHA-1 on both ends.
    private fun oaepSpec() =
        OAEPParameterSpec("SHA-256", "MGF1", MGF1ParameterSpec.SHA1, PSource.PSpecified.DEFAULT)

    private fun aliasFor(key: String) = "biovault_$key"

    private fun keyStore(): KeyStore = KeyStore.getInstance(keystoreName).apply { load(null) }

    private fun prefs() = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)

    /** Drop both the stored ciphertext and the (dead) keystore entry for a key. */
    private fun forget(alias: String) {
        try { prefs().edit().remove(alias).apply() } catch (_: Exception) {}
        try { keyStore().deleteEntry(alias) } catch (_: Exception) {}
    }

    @PluginMethod
    fun isAvailable(call: PluginCall) {
        val ok = BiometricManager.from(context)
            .canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG) ==
            BiometricManager.BIOMETRIC_SUCCESS
        call.resolve(JSObject().put("available", ok))
    }

    @PluginMethod
    fun set(call: PluginCall) {
        val key = call.getString("key") ?: run { call.reject("key is required"); return }
        val value = call.getString("value") ?: run { call.reject("value is required"); return }
        val alias = aliasFor(key)
        try {
            val ks = keyStore()
            if (ks.containsAlias(alias)) ks.deleteEntry(alias) // replace-on-write, like iOS

            val spec = KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_ECB)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_RSA_OAEP)
                .setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA1)
                .setUserAuthenticationRequired(true)
                .setInvalidatedByBiometricEnrollment(true)
                .build()
            val generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, keystoreName)
            generator.initialize(spec)
            val publicKey = generator.generateKeyPair().public

            // Public-key encryption needs no authentication.
            val cipher = Cipher.getInstance(transformation)
            cipher.init(Cipher.ENCRYPT_MODE, publicKey, oaepSpec())
            val ciphertext = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
            prefs().edit().putString(alias, Base64.encodeToString(ciphertext, Base64.NO_WRAP)).apply()
            call.resolve()
        } catch (e: Exception) {
            forget(alias)
            call.reject("vault set failed: ${e.message}")
        }
    }

    @PluginMethod
    fun get(call: PluginCall) {
        val key = call.getString("key") ?: run { call.reject("key is required"); return }
        val reason = call.getString("reason") ?: "Unlock InvestiKid"
        val alias = aliasFor(key)

        val ciphertextB64 = prefs().getString(alias, null)
            ?: run { call.resolve(JSObject()); return } // absent → gone

        val privateKey = try {
            keyStore().getKey(alias, null)
        } catch (e: Exception) {
            forget(alias); call.resolve(JSObject()); return // dead key → gone
        }
        if (privateKey == null) { forget(alias); call.resolve(JSObject()); return }

        val cipher = Cipher.getInstance(transformation)
        try {
            cipher.init(Cipher.DECRYPT_MODE, privateKey, oaepSpec())
        } catch (e: KeyPermanentlyInvalidatedException) {
            forget(alias); call.resolve(JSObject()); return // biometrics re-enrolled → gone
        } catch (e: Exception) {
            forget(alias); call.resolve(JSObject()); return
        }

        val ciphertext = Base64.decode(ciphertextB64, Base64.NO_WRAP)
        val host = activity as? FragmentActivity
            ?: run { call.reject("no host activity"); return }

        host.runOnUiThread {
            val prompt = BiometricPrompt(
                host,
                ContextCompat.getMainExecutor(context),
                object : BiometricPrompt.AuthenticationCallback() {
                    override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                        try {
                            val authedCipher = result.cryptoObject?.cipher ?: cipher
                            val plaintext = authedCipher.doFinal(ciphertext)
                            call.resolve(JSObject().put("value", String(plaintext, Charsets.UTF_8)))
                        } catch (e: KeyPermanentlyInvalidatedException) {
                            forget(alias); call.resolve(JSObject())
                        } catch (e: Exception) {
                            call.reject("decrypt failed: ${e.message}", "AUTH_FAILED")
                        }
                    }

                    override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                        call.reject("biometric error: $errString", "AUTH_FAILED")
                    }

                    override fun onAuthenticationFailed() {
                        // Transient non-match; the system prompt stays up for a retry.
                    }
                },
            )
            val info = BiometricPrompt.PromptInfo.Builder()
                .setTitle("Unlock InvestiKid")
                .setSubtitle(reason)
                .setNegativeButtonText("Cancel")
                .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
                .build()
            prompt.authenticate(info, BiometricPrompt.CryptoObject(cipher))
        }
    }

    @PluginMethod
    fun remove(call: PluginCall) {
        val key = call.getString("key") ?: run { call.reject("key is required"); return }
        forget(aliasFor(key))
        call.resolve()
    }
}
