import Foundation
import Capacitor
import LocalAuthentication
import Security

/// Biometric-bound secure storage (SP-Bio H1).
///
/// Stores the opaque server secret in the iOS Keychain with an access-control
/// object created using `.biometryCurrentSet`, so the item is released ONLY by
/// the biometric set enrolled at write time. Adding or removing a Face ID /
/// Touch ID enrolment invalidates the item — the OS drops it and the next
/// `get` returns `errSecItemNotFound`, which we surface as "gone" so the app
/// forgets the credential and falls back to password. This delivers the
/// re-enrolment-invalidation guarantee that a plain keychain (the previous
/// `@aparajita/capacitor-secure-storage`) cannot.
@objc(BiometricVaultPlugin)
public class BiometricVaultPlugin: CAPPlugin {

    /// Distinct from any aparajita keychain service so the two never collide.
    private let service = "ai.investikid.biometric-vault"

    @objc func isAvailable(_ call: CAPPluginCall) {
        let context = LAContext()
        var error: NSError?
        let ok = context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error)
        call.resolve(["available": ok])
    }

    @objc func set(_ call: CAPPluginCall) {
        guard let key = call.getString("key"),
              let value = call.getString("value"),
              let data = value.data(using: .utf8) else {
            call.reject("key and value are required")
            return
        }
        var acError: Unmanaged<CFError>?
        guard let access = SecAccessControlCreateWithFlags(
            nil,
            kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
            .biometryCurrentSet,
            &acError
        ) else {
            call.reject("access control unavailable (no passcode/biometrics?)")
            return
        }
        let service = self.service
        DispatchQueue.global(qos: .userInitiated).async {
            // Replace any prior item for this key (no prompt on delete/add).
            let base: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: service,
                kSecAttrAccount as String: key,
            ]
            SecItemDelete(base as CFDictionary)

            var addQuery = base
            addQuery[kSecValueData as String] = data
            addQuery[kSecAttrAccessControl as String] = access
            let status = SecItemAdd(addQuery as CFDictionary, nil)
            if status == errSecSuccess {
                call.resolve()
            } else {
                call.reject("keychain set failed (\(status))")
            }
        }
    }

    @objc func get(_ call: CAPPluginCall) {
        guard let key = call.getString("key") else {
            call.reject("key is required")
            return
        }
        let reason = call.getString("reason") ?? "Unlock InvestiKid"
        let context = LAContext()
        context.localizedReason = reason
        let service = self.service
        DispatchQueue.global(qos: .userInitiated).async {
            let query: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: service,
                kSecAttrAccount as String: key,
                kSecReturnData as String: true,
                kSecMatchLimit as String: kSecMatchLimitOne,
                kSecUseAuthenticationContext as String: context,
            ]
            var item: CFTypeRef?
            let status = SecItemCopyMatching(query as CFDictionary, &item)
            switch status {
            case errSecSuccess:
                if let data = item as? Data, let str = String(data: data, encoding: .utf8) {
                    call.resolve(["value": str])
                } else {
                    // Present but undecodable — treat as gone.
                    call.resolve([:])
                }
            case errSecItemNotFound:
                // Absent OR invalidated by a biometric re-enrolment → "gone".
                call.resolve([:])
            default:
                // User cancel / auth failure / lockout → keep the credential,
                // let the caller stay locked and retry.
                call.reject("biometric authentication failed", "AUTH_FAILED")
            }
        }
    }

    @objc func remove(_ call: CAPPluginCall) {
        guard let key = call.getString("key") else {
            call.reject("key is required")
            return
        }
        let service = self.service
        DispatchQueue.global(qos: .userInitiated).async {
            let query: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: service,
                kSecAttrAccount as String: key,
            ]
            let status = SecItemDelete(query as CFDictionary)
            if status == errSecSuccess || status == errSecItemNotFound {
                call.resolve()
            } else {
                call.reject("keychain remove failed (\(status))")
            }
        }
    }
}
