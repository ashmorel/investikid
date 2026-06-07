import Foundation
import Capacitor
import StoreKit

@objc(StoreKitPlugin)
public class StoreKitPlugin: CAPPlugin {

    @objc func getProducts(_ call: CAPPluginCall) {
        guard let ids = call.getArray("productIds", String.self) else {
            call.reject("productIds required"); return
        }
        Task {
            do {
                let products = try await Product.products(for: ids)
                let out = products.map { ["id": $0.id, "displayPrice": $0.displayPrice, "displayName": $0.displayName] }
                call.resolve(["products": out])
            } catch { call.reject("getProducts failed: \(error.localizedDescription)") }
        }
    }

    @objc func purchase(_ call: CAPPluginCall) {
        guard let productId = call.getString("productId"),
              let tokenStr = call.getString("appAccountToken"),
              let token = UUID(uuidString: tokenStr) else {
            call.reject("productId and a UUID appAccountToken are required"); return
        }
        Task {
            do {
                let products = try await Product.products(for: [productId])
                guard let product = products.first else { call.reject("Unknown product"); return }
                let result = try await product.purchase(options: [.appAccountToken(token)])
                switch result {
                case .success(let verification):
                    let jws = verification.jwsRepresentation
                    if case .verified(let transaction) = verification { await transaction.finish() }
                    call.resolve(["jws": jws])
                case .userCancelled: call.reject("cancelled", "USER_CANCELLED")
                case .pending: call.resolve(["pending": true])
                @unknown default: call.reject("unknown purchase result")
                }
            } catch { call.reject("purchase failed: \(error.localizedDescription)") }
        }
    }

    @objc func restore(_ call: CAPPluginCall) {
        Task {
            var jwsList: [String] = []
            for await result in Transaction.currentEntitlements {
                jwsList.append(result.jwsRepresentation)
            }
            call.resolve(["jws": jwsList])
        }
    }
}
