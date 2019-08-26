import json
import re
import time
from concurrent.futures.thread import ThreadPoolExecutor

import pymysql
import requests

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36'
}
pool = ThreadPoolExecutor(8)


def get_episode(page):
    db = pymysql.connect("127.0.0.1", "root", "mlbj", "shows")
    ex = db.cursor()
    sql = 'select id,episode_url_path,episode_url from episode limit %s,%s' % (page * 500, (page + 1) * 500)
    ex.execute(sql)
    result = ex.fetchall()
    for data in result:
        episode_id = data[0]
        episode_url = data[1]

        pool.submit(get_episode_url, episode_url, episode_id)
        # download_video(episode_url, episode_name, movie_name)
    db.close()


def get_episode_url(episode_url, episode_id):
    time.sleep(3)
    db = pymysql.connect("127.0.0.1", "root", "mlbj", "shows")
    s = requests.session()
    s.keep_alive = False
    url = "https://www.crunchyroll.com"+episode_url.replace("\\", " ")
    res = s.get(url, headers=headers)
    url_m3u8 = []

    try:
        data = res.text
        data = re.findall("vilos\.config\.media = ([\w\W]*?)\}\]\};", data)
        if len(data) == 0:
            print("未找到资源----")
            url_m3u8.append("null")
            return
        data = data[0] + "}]}"
        data = json.loads(data)
        for u in data['streams']:
            if u["url"].find(".m3u8") != -1:
                url_m3u8.append(u)
        ls = json.dumps(url_m3u8)
        sql = "update episode set episode_url = '%s' where id =%s" % (str(ls), episode_id)
        ex = db.cursor()
        ex.execute(sql)
        db.commit()
        print(episode_url + "更新成功")
    except Exception as e:
        print(e)
        db.rollback()
        raise e
    db.close()


def update_m3u8():
    db = pymysql.connect("127.0.0.1", "root", "root@cpx", "shows")
    sql = "select id, episode_url from episode "
    ex = db.cursor()
    ex.execute(sql)
    result = ex.fetchall()
    for data in result:
        episode_id = data[0]
        episode_url = data[1]
        episode_url = episode_url.replace("None", "null").replace("'", "\"")
        ls = json.dumps(episode_url)
        print(str(ls))
        update_sql = "update episode set episode_url='%s' where id= %s" % (ls, episode_id)
        ex.execute(update_sql)
        db.commit()
        print("更新完成" + str(episode_id))


if __name__ == '__main__':
    for page in range(0, 24):
        print("开始")
        get_episode(page)
    # update_m3u8()
