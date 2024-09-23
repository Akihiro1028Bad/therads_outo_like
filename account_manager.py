import json
import threading
from main import setup_driver, login_to_threads, get_recommended_posts, auto_like_comments_on_posts
import logging
from cookie_manager import save_cookies, load_cookies, delete_cookies
import time
from collections import defaultdict

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_accounts(file_path):
    """
    JSONファイルからアカウント情報を読み込む

    :param file_path: JSONファイルのパス
    :return: アカウント情報のリスト
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            accounts = json.load(file)
        logging.info(f"{len(accounts)}件のアカウント情報を読み込みました。")
        return accounts
    except FileNotFoundError:
        logging.error(f"ファイル {file_path} が見つかりません。")
        return []
    except json.JSONDecodeError:
        logging.error(f"ファイル {file_path} の解析に失敗しました。JSONフォーマットを確認してください。")
        return []

# process_account 関数を以下のように修正
def process_account(account):
    """
    1つのアカウントに対して自動いいね処理を実行する

    :param account: アカウント情報の辞書
    """
    username = account['username']
    password = account['password']
    num_likes = account.get('num_likes', 10)  # デフォルト値を10に設定

    #取得したユーザ情報
    logging.info(f"----------------------------------------")
    logging.info(f"ユーザ名：{username} ")
    logging.info(f"パスワード：{password} ")
    logging.info(f"投稿数：{num_likes} ")
    logging.info(f"----------------------------------------")

    driver = setup_driver()
    try:
        if login_to_threads(driver, username, password):
            post_urls = get_recommended_posts(driver, username, num_likes)
            success, likes_count = auto_like_comments_on_posts(driver, post_urls, account['username'])

            if not success:
                logging.info(f"アカウント {username}: 制限が検知されたため、処理を終了します。")
                # 処理成功後、最新のクッキーを保存
                save_cookies(driver, username)
                logging.info(f"アカウント {username}: クッキーを保存しました。")

                return likes_count, "制限検知"
            else:
                logging.info(f"アカウント {username}: 処理が正常に完了しました。合計 {likes_count} 件のいいねを行いました。")
                # 処理成功後、最新のクッキーを保存
                save_cookies(driver, username)
                logging.info(f"アカウント {username}: クッキーを保存しました。")

                return likes_count, "処理成功"
        else:
            logging.error(f"アカウント {username}: ログインに失敗したため、自動「いいね」を実行できません。")
            return 0, "処理失敗"
    except Exception as e:
        logging.error(f"アカウント {username}: 予期せぬエラーが発生しました: {e}")
        return 0, "処理失敗"
    finally:
        driver.quit()
        logging.info(f"アカウント {username}: ブラウザを終了しました。")

def process_account_batch(batch):
    """
    アカウントのバッチを処理する関数

    :param batch: 処理するアカウントのリスト
    :return: アカウントごとの処理結果を含む辞書
    """
    batch_results = {}
    for account in batch:
        try:
            likes_count, status = process_account(account)
            batch_results[account['username']] = {"likes": likes_count, "status": status}
        except Exception as e:
            logging.error(f"アカウント {account['username']} の処理中に予期せぬエラーが発生しました: {str(e)}")
            batch_results[account['username']] = {"likes": 0, "status": "処理失敗"}
    return batch_results

def display_all_results(results):
    """
    全アカウントの処理結果を表示する関数

    :param results: アカウントごとの処理結果を含む辞書
    """
    logging.info("=" * 70)
    logging.info("全アカウントの処理結果:")
    logging.info("=" * 70)
    logging.info(f"{'アカウント':<20} {'状態':<15} {'いいね数':<10}")
    logging.info("-" * 70)
    
    total_likes = 0
    total_restricted = 0
    total_failed = 0
    
    for username, result in results.items():
        status = result['status']
        likes = result['likes']
        
        if status == "制限検知":
            total_restricted += 1
            total_likes += likes
        elif status == "処理失敗":
            total_failed += 1
            total_likes += likes
        else:
            total_likes += likes
        
        logging.info(f"{username:<20} {status:<15} {likes:<10}")
    
    logging.info("=" * 70)
    logging.info(f"総いいね数: {total_likes}")
    logging.info(f"制限検知アカウント数: {total_restricted}")
    logging.info(f"処理失敗アカウント数: {total_failed}")
    logging.info("=" * 70)

def run_accounts_in_batches(accounts, batch_size=5):
    """
    アカウントをバッチで実行する関数

    :param accounts: 全アカウントのリスト
    :param batch_size: 1バッチあたりのアカウント数（デフォルト: 5）
    """
    total_accounts = len(accounts)
    results = {}

    for i in range(0, total_accounts, batch_size):
        batch = accounts[i:i+batch_size]
        logging.info(f"バッチ処理開始: アカウント {i+1} から {min(i+batch_size, total_accounts)} まで（全 {total_accounts} アカウント中）")
        try:
            batch_results = process_account_batch(batch)
            results.update(batch_results)
        except Exception as e:
            logging.error(f"バッチ処理中に予期せぬエラーが発生しました: {str(e)}")
        
        display_all_results(results)
        
        if i + batch_size < total_accounts:
            wait_time = 60  # バッチ間の待機時間（秒）
            logging.info(f"次のバッチの処理まで {wait_time} 秒待機します。")
            time.sleep(wait_time)

    display_all_results(results)

        