package leeashmore.investikid.ai.app

import com.android.billingclient.api.*
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

@CapacitorPlugin(name = "PlayBilling")
class PlayBillingPlugin : Plugin() {

    private var billingClient: BillingClient? = null
    private var pendingCall: PluginCall? = null

    private fun client(onReady: (BillingClient) -> Unit, onError: (String) -> Unit) {
        val existing = billingClient
        if (existing != null && existing.isReady) { onReady(existing); return }
        val c = BillingClient.newBuilder(context)
            .enablePendingPurchases()
            .setListener { result, purchases -> onPurchases(result, purchases) }
            .build()
        billingClient = c
        c.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) onReady(c)
                else onError("Billing setup failed: ${result.responseCode}")
            }
            override fun onBillingServiceDisconnected() { }
        })
    }

    private fun onPurchases(result: BillingResult, purchases: List<Purchase>?) {
        val call = pendingCall ?: return
        pendingCall = null
        when (result.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                val p = purchases?.firstOrNull()
                if (p == null) { call.resolve(JSObject().put("pending", true)); return }
                call.resolve(JSObject().put("purchaseToken", p.purchaseToken)
                    .put("productId", p.products.firstOrNull() ?: ""))
            }
            BillingClient.BillingResponseCode.USER_CANCELED -> call.reject("cancelled", "USER_CANCELLED")
            else -> call.reject("purchase failed: ${result.responseCode}")
        }
    }

    @PluginMethod
    fun getProducts(call: PluginCall) {
        val ids = call.getArray("productIds") ?: run { call.reject("productIds required"); return }
        val productList = (0 until ids.length()).map {
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(ids.getString(it))
                .setProductType(BillingClient.ProductType.SUBS).build()
        }
        client({ c ->
            val params = QueryProductDetailsParams.newBuilder().setProductList(productList).build()
            c.queryProductDetailsAsync(params) { result, details ->
                if (result.responseCode != BillingClient.BillingResponseCode.OK) {
                    call.reject("getProducts failed: ${result.responseCode}"); return@queryProductDetailsAsync
                }
                val arr = JSArray()
                details.forEach { d ->
                    val offer = d.subscriptionOfferDetails?.firstOrNull()
                    val price = offer?.pricingPhases?.pricingPhaseList?.firstOrNull()?.formattedPrice ?: ""
                    arr.put(JSObject().put("id", d.productId).put("displayPrice", price).put("displayName", d.name))
                }
                call.resolve(JSObject().put("products", arr))
            }
        }, { call.reject(it) })
    }

    @PluginMethod
    fun purchase(call: PluginCall) {
        val productId = call.getString("productId") ?: run { call.reject("productId required"); return }
        val account = call.getString("obfuscatedAccountId") ?: run { call.reject("obfuscatedAccountId required"); return }
        client({ c ->
            val params = QueryProductDetailsParams.newBuilder().setProductList(listOf(
                QueryProductDetailsParams.Product.newBuilder()
                    .setProductId(productId).setProductType(BillingClient.ProductType.SUBS).build())).build()
            c.queryProductDetailsAsync(params) { r, details ->
                val d = details.firstOrNull()
                if (r.responseCode != BillingClient.BillingResponseCode.OK || d == null) {
                    call.reject("Unknown product"); return@queryProductDetailsAsync
                }
                val offerToken = d.subscriptionOfferDetails?.firstOrNull()?.offerToken
                if (offerToken == null) { call.reject("No subscription offer"); return@queryProductDetailsAsync }
                val flowParams = BillingFlowParams.newBuilder()
                    .setProductDetailsParamsList(listOf(
                        BillingFlowParams.ProductDetailsParams.newBuilder()
                            .setProductDetails(d).setOfferToken(offerToken).build()))
                    .setObfuscatedAccountId(account)
                    .build()
                pendingCall = call
                activity.runOnUiThread { c.launchBillingFlow(activity, flowParams) }
            }
        }, { call.reject(it) })
    }

    @PluginMethod
    fun restore(call: PluginCall) {
        client({ c ->
            c.queryPurchasesAsync(QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.SUBS).build()) { r, purchases ->
                if (r.responseCode != BillingClient.BillingResponseCode.OK) {
                    call.reject("restore failed: ${r.responseCode}"); return@queryPurchasesAsync
                }
                val arr = JSArray(); purchases.forEach { arr.put(it.purchaseToken) }
                call.resolve(JSObject().put("purchaseTokens", arr))
            }
        }, { call.reject(it) })
    }
}
