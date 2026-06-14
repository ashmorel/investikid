import UIKit
import Capacitor
import WebKit
import FirebaseCore
import FirebaseMessaging

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Configure Firebase only when GoogleService-Info.plist is bundled, so a
        // build without it still launches (push simply never yields a token).
        if Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist") != nil {
            FirebaseApp.configure()
        }
        return true
    }

    // iOS delivered the APNs token. Hand it to Firebase, fetch the FCM
    // registration token, and post it as a String so @capacitor/push-notifications
    // emits it on the "registration" event (push.ts then registers it). FCM tokens
    // — not raw APNs tokens — are what the backend's FCM HTTP v1 sender requires.
    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        guard FirebaseApp.app() != nil else {
            // No GoogleService-Info.plist in this build → no FCM token available.
            NotificationCenter.default.post(
                name: .capacitorDidFailToRegisterForRemoteNotifications,
                object: NSError(domain: "InvestiKidPush", code: -1,
                                userInfo: [NSLocalizedDescriptionKey: "Firebase not configured"])
            )
            return
        }
        Messaging.messaging().apnsToken = deviceToken
        Messaging.messaging().token { token, error in
            if let token = token {
                NotificationCenter.default.post(
                    name: .capacitorDidRegisterForRemoteNotifications,
                    object: token
                )
            } else {
                NotificationCenter.default.post(
                    name: .capacitorDidFailToRegisterForRemoteNotifications,
                    object: error
                )
            }
        }
    }

    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        NotificationCenter.default.post(
            name: .capacitorDidFailToRegisterForRemoteNotifications,
            object: error
        )
    }

    func applicationWillResignActive(_ application: UIApplication) {
        // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
        // Use this method to pause ongoing tasks, disable timers, and invalidate graphics rendering callbacks. Games should use this method to pause the game.
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later.
        // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        // Called as part of the transition from the background to the active state; here you can undo many of the changes made on entering the background.
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        // On a cold launch WKWebView can end up WIDER than its container, so
        // content spills past the right edge until a background/foreground cycle
        // re-lays it out. We replicate that re-layout: snap the web view back to
        // its parent's bounds (the correct screen width) and force a layout pass.
        // Repeated across the launch-settling window because didBecomeActive can
        // fire before the safe-area/splash settle on a cold start.
        relayoutWebView(attempt: 0)
    }

    private func relayoutWebView(attempt: Int) {
        let delay = attempt == 0 ? 0.05 : 0.25
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self else { return }
            if let webView = self.findWebView(in: self.window?.rootViewController?.view),
               let parent = webView.superview {
                if webView.frame != parent.bounds {
                    webView.frame = parent.bounds  // correct the too-wide frame
                }
                parent.setNeedsLayout()
                parent.layoutIfNeeded()
                webView.setNeedsLayout()
                webView.layoutIfNeeded()
            }
            if attempt < 4 { self.relayoutWebView(attempt: attempt + 1) }
        }
    }

    private func findWebView(in view: UIView?) -> WKWebView? {
        guard let view = view else { return nil }
        if let webView = view as? WKWebView { return webView }
        for subview in view.subviews {
            if let found = findWebView(in: subview) { return found }
        }
        return nil
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
    }

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        // Called when the app was launched with a url. Feel free to add additional processing here,
        // but if you want the App API to support tracking app url opens, make sure to keep this call
        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)
    }

    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        // Called when the app was launched with an activity, including Universal Links.
        // Feel free to add additional processing here, but if you want the App API to support
        // tracking app url opens, make sure to keep this call
        return ApplicationDelegateProxy.shared.application(application, continue: userActivity, restorationHandler: restorationHandler)
    }

}
