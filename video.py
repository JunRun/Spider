import json
import re
import pymysql
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import uuid
import subprocess

import requests
import os

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36",
}
dir_path = "/Volumes/videos/crunchyroll_video/"
pool = ThreadPoolExecutor(1)


# 获取动漫列表
def get_movie():
    db = pymysql.connect("localhost", "root", "root@cpx", "shows")
    ex = db.cursor()
    sql = "select id,movie_name from movie"
    ex.execute(sql)
    result = ex.fetchall()
    for data in result:
        movie_name = data[1]
        movie_id = data[0]
        movie_dir_path = dir_path + movie_name
        if not os.path.exists(movie_dir_path):
            os.mkdir(movie_dir_path)
        get_episode(movie_id, movie_name)


# 获取剧集列表
def get_episode(movie_id, movie_name):
    db = pymysql.connect("127.0.0.1", "root", "root@cpx", "shows")
    ex = db.cursor()
    sql = 'select id,episode_url,episode_name,right(episode_number,3) from episode where movie_id = "%s" and download = 0 ' % movie_id
    ex.execute(sql)
    result = ex.fetchall()
    for data in result:
        episode_id = data[0]
        episode_url = data[1]
        episode_name = data[2]
        episode_number = data[3].replace("\n", "")
        if (episode_number == "e1") or (episode_number == "e2") or (episode_number == "e3"):
            pool.submit(download_video, episode_id, episode_url, episode_name, movie_name)
        # download_video(episode_url, episode_name, movie_name)
    db.close()


# 下载视频
def download_video(episode_id, episode_url, episode_name, movie_name):
    country = ""
    url = "https://www.crunchyroll.com" + country + episode_url
    res = requests.get(url, headers=headers)
    try:
        data = res.text
        data = re.findall("vilos\.config\.media = ([\w\W]*?)\}\]\};", data)
        if len(data) == 0:
            print("未找到资源----")
            return
        data = data[0] + "}]}"
        data = json.loads(data)
        en_url = ""
        for u in data['streams']:
            if u['hardsub_lang'] == 'enUS':
                en_url = u['url']
                if en_url.find(".m3u8") != -1:
                    break
        print(movie_name + ":" + episode_name + "  开始下载")
        cdPath = "/Volumes/videos/crunchyroll_video/"
        episode_name = str(uuid.uuid1())
        movie_name = movie_name.replace(" ", "\ ")

        os.system('cd '+cdPath+movie_name+' && ffmpeg -i "'+en_url+'" "'+episode_name+'.mp4"')
        print(movie_name + ":" + episode_name + " 下载 完成")
        episode_url = movie_name+"/"+episode_name+".mp4"
        update_episode(episode_id, episode_url)
    except Exception as e:
        print(e)
        raise


def update_episode(episode_id, episode_url):
    db = pymysql.connect("127.0.0.1", "root", "root@cpx", "shows")
    ex = db.cursor()
    try:
        sql = "update episode set download = 1 , episode_url = '%s' where id = '%s'" % (episode_url, episode_id)
        ex.execute(sql)
        db.commit()
        print("更新完成")

    except Exception as e:
        print(e)
        db.rollback()
    db.close()


if __name__ == "__main__":
    print("begin")
    get_movie()
    # print("begin")
    # url = "/boruto-naruto-next-generations/episode-118-something-that-steals-memories-786486"
    # dir_url = "Volumes/My\ Book/crunchyroll_video"
    # video_file = download_video(url)
    # print(video_file)
    # httpCode = 'export http_proxy= "http://127.0.0.1:8001"; export HTTP_PROXY="http://127.0.0.1:8001"; export https_proxy="http://127.0.0.1:8001"; export HTTPS_PROXY="http://127.0.0.1:8001"'
    # os.system(httpCode + "&& ffmpeg -i '" + video_file + "' 'syyy.mp4'")
