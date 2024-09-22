import sys
import time
import logging
import json
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from bs4 import BeautifulSoup
import time

# ログの設定：日時、ログレベル、メッセージを表示
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver():
    """
    Chromeドライバーを設定し、初期化する関数
    
    戻り値:
    - driver: 設定済みのWebDriverオブジェクト
    """
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # ヘッドレスモードを使用する場合はコメントを外す
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    logging.info("Chromeドライバーを正常に設定しました。")
    return driver

def login_to_threads(driver, username, password):
    """
    Threadsにログインする関数
    
    引数:
    - driver: WebDriverオブジェクト
    - username: ログイン用のユーザー名
    - password: ログイン用のパスワード
    
    戻り値:
    - bool: ログイン成功時はTrue、失敗時はFalse
    """
    url = "https://www.threads.net/login/"
    try:
        driver.get(url)
        logging.info(f"ログインページにアクセスしています: {url}")
        
        # ユーザー名入力フィールドを待機し、入力
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'][class*='x1i10hfl'][class*='x1a2a7pz']"))
        )
        username_field.clear()
        username_field.send_keys(username)
        logging.info("ユーザー名を入力しました")
        
        # パスワード入力フィールドを見つけ、入力
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(password)
        logging.info("パスワードを入力しました")
        
        # 入力後、短い待機時間を設定
        time.sleep(2)
        
        # ログインボタンを見つけてクリック
        login_button_xpath = "//div[@role='button' and contains(@class, 'x1i10hfl') and contains(@class, 'x1qjc9v5')]//div[contains(text(), 'Log in') or contains(text(), 'ログイン')]"
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, login_button_xpath))
        )
        driver.execute_script("arguments[0].click();", login_button)
        logging.info("ログインボタンをクリックしました")

        time.sleep(20)
        
        # ページの読み込みを待機
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logging.info("ログインが完了し、ページが正常に読み込まれました")

        time.sleep(5)
        
        # ログイン成功後、クッキーを保存
        save_cookies(driver, "threads_cookies.pkl")
        logging.info("ログインセッションのクッキーを保存しました")
        
        return True
    except Exception as e:
        logging.error(f"ログイン処理中にエラーが発生しました: {e}")
        return False

def save_cookies(driver, file_path):
    """
    現在のセッションのクッキーを保存する関数
    
    引数:
    - driver: WebDriverオブジェクト
    - file_path: クッキーを保存するファイルのパス
    """
    with open(file_path, "wb") as file:
        pickle.dump(driver.get_cookies(), file)
    logging.info(f"クッキーを {file_path} に保存しました")

def load_cookies(driver, file_path):
    """
    保存されたクッキーを読み込む関数
    
    引数:
    - driver: WebDriverオブジェクト
    - file_path: 保存されたクッキーファイルのパス
    """
    with open(file_path, "rb") as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
    logging.info(f"{file_path} からクッキーを読み込み、ブラウザに適用しました")

def get_recommended_posts(driver, num_posts=10):
    """
    おすすめ投稿を取得する関数
    
    引数:
    - driver: WebDriverオブジェクト
    - num_posts: 取得する投稿の数（デフォルト: 10）
    
    戻り値:
    - list: 取得した投稿のURLリスト
    """
    url = "https://www.threads.net"
    post_hrefs = []
    last_height = 0
    reload_counter = 0

    while len(post_hrefs) < num_posts:
        # 10投稿ごと、または初回にページをロード/リロード
        if reload_counter % 10 == 0:
            driver.get(url)
            load_cookies(driver, "threads_cookies.pkl")
            driver.refresh()
            logging.info(f"ページをロード/リロードしました。現在の投稿数: {len(post_hrefs)}")
            time.sleep(5)
            last_height = driver.execute_script("return document.body.scrollHeight")
            reload_counter = 0

        # ページの最下部までスクロール
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)  # コンテンツの読み込みを待機
        
        # 新しい投稿URLを取得
        new_hrefs = get_post_hrefs(driver.page_source)
        for href in new_hrefs:
            if href not in post_hrefs:
                post_hrefs.append(href)
                reload_counter += 1
                if len(post_hrefs) >= num_posts:
                    break
                if reload_counter % 10 == 0:
                    break  # 10投稿取得したらすぐにリロード

        # スクロールが最下部に達したかチェック
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            logging.info("ページの最下部に到達しました。これ以上の投稿は読み込めません。")
            break
        last_height = new_height

    logging.info(f"合計 {len(post_hrefs)} 件のおすすめ投稿URLを取得しました")
    # 取得したURLをすべて表示
    logging.info("取得した投稿のURL一覧:")
    for i, href in enumerate(post_hrefs, 1):
        logging.info(f"{i}. https://www.threads.net{href}")
        
    return post_hrefs[:num_posts]

def get_post_hrefs(html_content):
    """
    HTML内の投稿URLを抽出する関数
    
    引数:
    - html_content: 解析するHTMLコンテンツ
    
    戻り値:
    - list: 抽出された投稿URLのリスト
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    post_hrefs = []
    elements = soup.find_all('a', class_=['x1i10hfl', 'x1lliihq'], href=True)
    for element in elements:
        href = element['href']
        if '/post/' in href and href not in post_hrefs:
            post_hrefs.append(href)
    return post_hrefs

def click_all_like_buttons(driver, post_url, total_likes, login_username, max_scroll_attempts=5, scroll_pause_time=2):
    """
    指定された投稿ページ内のすべての「いいね！」ボタンをクリックする関数。
    
    :param driver: Seleniumのウェブドライバーインスタンス
    :param post_url: 処理する投稿のURL
    :param max_scroll_attempts: 最大スクロール試行回数（デフォルト: 5）
    :param scroll_pause_time: スクロール後の待機時間（秒）（デフォルト: 2）
    :return: クリックした「いいね！」ボタンの合計数
    """
    logging.info(f"投稿 {post_url} の「いいね！」ボタンクリック処理を開始します。")
    new_post_url = f"https://www.threads.net{post_url}" if not post_url.startswith("https://") else post_url

    def safe_click(element):
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            logging.error(f"クリック中に予期せぬエラーが発生しました: {str(e)}")
            return False

    def check_like_status(button):
        try:
            svg = button.find_element(By.CSS_SELECTOR, "svg[aria-label='「いいね！」']")
            fill_value = svg.find_element(By.TAG_NAME, "path").get_attribute("fill")
            return fill_value != "transparent" and fill_value is not None
        except Exception:
            return False

    try:
        driver.get(new_post_url)
        logging.info(f"投稿ページにアクセスしています: {new_post_url}")

        # ページの読み込みを待機
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logging.info("投稿ページが正常に読み込まれました")

        click_count = 0
        new_total_likes = total_likes

        for scroll_attempt in range(max_scroll_attempts):
            logging.info(f"スクロール試行 {scroll_attempt + 1}/{max_scroll_attempts}")
            
            # 更新されたセレクタを使用して「いいね！」ボタンを探す
            like_buttons = driver.find_elements(By.CSS_SELECTOR, "div[role='button'][tabindex='0'] div.x6s0dn4")

            #制限チェック用
            count = 0
            check_interval = 10
            
            if not like_buttons:
                logging.info("「いいね！」ボタンが見つかりません。スクロールを続行します。")
            else:
                for button in like_buttons:
                    try:
                        # SVG要素を探してフィル状態を確認
                        svg = button.find_element(By.CSS_SELECTOR, "svg[aria-label='「いいね！」']")
                        fill_value = svg.find_element(By.TAG_NAME, "path").get_attribute("fill")
                        
                        if fill_value == "transparent" or not fill_value:
                            if safe_click(button):
                                click_count += 1
                                logging.info(f"「いいね！」ボタンをクリックしました。合計: {click_count}")
                                time.sleep(0.5)  # クリック後の短い待機

                                count = count + 1
                                new_total_likes = new_total_likes + 1

                            # 10回ごとに制限チェック
                            if new_total_likes % 10 == 0:
                                logging.info("★ 10いいねしたので制限チェックします") 
                                time.sleep(2)
                                
                                # SVG要素を探してフィル状態を確認
                                try:
                                    svg = button.find_element(By.CSS_SELECTOR, "svg[aria-label='「いいね！」']")
                                    
                                    if svg:
                                        logging.info("=" * 50)
                                        logging.info(f"制限を感知しました")
                                        logging.info(f"ユーザー名: {login_username}")
                                        logging.info(f"合計いいね数: {new_total_likes}")
                                        logging.info("制限が感知されたため、処理を中止します。")
                                        logging.info("=" * 50)
                                        return -1  # 制限を示す特別な値を返す

                                except NoSuchElementException:
                                    logging.info("★　制限は感知されませんでした。処理を続行します。")

                        else:
                            logging.debug("既にいいね済みのボタンをスキップしました")

                    except StaleElementReferenceException:
                        #logging.warning("要素が古くなっています。スキップして次に進みます。")
                        continue
                    except NoSuchElementException:
                        #logging.warning("SVG要素が見つかりませんでした。スキップします。")
                        continue
                    except Exception as e:
                        logging.error(f"ボタンクリック中に予期せぬエラーが発生しました: {str(e)}")

            # ページをスクロール
            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logging.info("これ以上スクロールできません。処理を終了します。")
                break
        
        logging.info(f"---------------------------------------------------------")
        logging.info(f"合計 {click_count} 件の「いいね！」ボタンをクリックしました。")
        logging.info(f"---------------------------------------------------------")
        return click_count

    except TimeoutException:
        logging.error(f"ページの読み込みがタイムアウトしました: {new_post_url}")
        return 0
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {str(e)}")
        return 0

def auto_like_comments_on_posts(driver, post_urls, login_username, delay=2):
    """
    複数の投稿のコメントに自動でいいねをする関数

    :param driver: WebDriverオブジェクト
    :param post_urls: いいねを押す投稿URLのリスト
    :param delay: 各投稿処理の間の待機時間（秒、デフォルト: 2）
    :return: いいねした合計コメント数
    """
    total_likes = 0
    total_posts = len(post_urls)

    for index, url in enumerate(post_urls, start=1):
        logging.info(f"処理中: {index}/{total_posts} - {url}")
        
        likes = click_all_like_buttons(driver, url, total_likes, login_username)
        
        if likes == -1:  # 制限が検知された場合
            return -1  # メイン関数に制限を通知

        total_likes += likes
        
        logging.info(f"投稿 {url} で {likes} 件のコメントにいいねしました。")
        
        # レート制限を回避するための待機
        time.sleep(delay)
        
        # 進捗報告
        logging.info(f"---------------------------------------------------------")
        logging.info(f"進捗: 合計 {total_likes} 件のコメントにいいねしました（{index}/{total_posts} 投稿処理済み）")
        logging.info(f"---------------------------------------------------------")

    logging.info(f"すべての投稿の処理が完了しました。合計 {total_likes} 件のコメントにいいねしました。")
    return total_likes

def main():
    """
    メイン実行関数
    ユーザー入力を受け取り、ログインと自動「いいね」処理を実行
    """
    login_username = input("Threadsのログインユーザー名を入力してください: ").strip()
    login_password = input("Threadsのパスワードを入力してください: ").strip()
    num_likes = int(input("「いいね」する投稿数を入力してください: ").strip())
    
    driver = setup_driver()
    
    try:
        if login_to_threads(driver, login_username, login_password):
            post_urls = get_recommended_posts(driver, num_likes)
            result = auto_like_comments_on_posts(driver, post_urls, login_username)

            if result == -1:
                logging.warning("制限が検知されたため、処理を終了します。")
            else:
                logging.info(f"処理が正常に完了しました。合計 {result} 件のいいねを行いました。")

        else:
            logging.error("ログインに失敗したため、自動「いいね」を実行できません。")
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}")
    finally:
        driver.quit()
        logging.info("ブラウザを終了しました。プログラムを終了します。")

    input("Enterキーを押して終了してください...")  # コマンドプロンプトを開いたままにする

if __name__ == "__main__":
    main()