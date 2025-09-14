import Foundation
import UIKit

// --- 시나리오 1: 'typealias'를 이용한 상속 관계 추상화 ---
public typealias BaseController = UIViewController

// 'BaseController'를 상속하지만, 실제로는 'UIViewController'를 상속합니다.
// 룰베이스는 이 관계를 놓칠 수 있습니다.
final class AliasedInheritanceController: BaseController {

    override func viewDidLoad() {
        super.viewDidLoad()
        let button = UIButton()
        button.addTarget(self, action: #selector(handleTap), for: .touchUpInside)
    }

    @objc private func handleTap() {
        print("Button tapped!")
    }
}


// --- 시나리오 2: 'typealias'를 이용한 프로토콜 조합 추상화 ---
protocol Trackable {
    var eventName: String { get }
}
typealias Serializable = Codable

// 'Serializable'과 'Trackable'을 조합한 별칭
typealias AnalyticsEvent = Serializable & Trackable

// 'AnalyticsEvent'를 채택했지만, 실제로는 'Codable'과 'Trackable'을 모두 준수해야 합니다.
// 룰베이스는 'Codable'을 직접적으로 인지하기 어렵습니다.
struct UserLoginEvent: AnalyticsEvent {
    let eventName = "user_login"
    let userId: String
    let timestamp: Date
}


// --- 시나리오 3: 외부 라이브러리/모듈의 불투명성 (시뮬레이션) ---

// 'ExternalFramework'라는 외부 모듈이 있다고 가정합니다.
// 우리는 이 모듈의 소스 코드를 볼 수 없습니다.
protocol ExternalFrameworkView {}
open class BaseView: UIView, ExternalFrameworkView {
    // 외부 라이브러리의 BaseView
}

// 'BaseView'를 상속합니다.
// 룰베이스는 'MyCustomView'가 'UIView'의 하위 클래스라는 사실을 직접 알 수 없습니다.
class MyCustomView: BaseView {
    override func layoutSubviews() {
        super.layoutSubviews()
    }
}


// --- 시나리오 4: 동적인 설정 값에 따른 분기 처리 ---

// 룰베이스는 'screenName' 문자열의 최종 값을 알 수 없어 'ProfileScreen' 클래스와의 연결고리를 찾지 못합니다.
func routeToScreen(with config: [String: Any]) {
    guard let screenName = config["screen_name"] as? String else {
        return
    }

    // 이 함수는 문자열 이름으로 뷰 컨트롤러를 생성한다고 가정합니다.
    _ = instantiateViewController(withName: screenName)
}

// 동적으로 생성될 수 있는 클래스
class ProfileScreen: UIViewController {
    // ...
}

// 위 함수들을 사용하는 예시
func applicationDidLaunch() {
    let navigationConfig = ["screen_name": "ProfileScreen"]
    routeToScreen(with: navigationConfig)
}

// 존재하지 않는 함수 (테스트용 스텁)
func instantiateViewController(withName name: String) -> UIViewController? {
    print("Attempting to instantiate \(name)...")
    return nil
}