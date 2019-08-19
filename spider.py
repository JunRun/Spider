import requests
from lxml import etree
import pymysql
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import time


headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36'
}


# 获取视频id,名字，图片
def get_video_id(url, page):
    time.sleep(1)
    url = url + str(page)
    s = requests.session()
    s.keep_alive = False
    res = s.get(url, headers=headers)
    html = etree.HTML(res.content)
    for rows in range(1, 41):
        rows = str(rows)
        video_id = html.xpath("//li[" + rows + "]/@id")
        expisode_url = html.xpath("//li[" + rows + "]/div/a/@href")
        video_img = html.xpath("//li[" + rows + "]/div/a/span[1]/img/@src")
        video_name = html.xpath("//li[" + rows + "]/div/a/span[2]/text()")
        if len(video_id):
            arry = get_more_info(str(expisode_url[0]), video_id)
            movie_insert(video_id[0], video_name[0], video_img[0], expisode_url[0], arry[2], arry[1], arry[0])
        else:
            break

    return 0


# 获取视频评分，描述，年份，分类
def get_more_info(name, movie_id):
    movie_url = "https://www.crunchyroll.com" + name + "/videos"
    s = requests.session()
    s.keep_alive = False
    res = s.get(movie_url, headers=headers)
    html = etree.HTML(res.content)
    video_info = html.xpath("//*[@id='sidebar_elements']/li[3]/p[2]/span[2]/text()")
    if len(video_info) == 0:
        video_info = html.xpath("//*[@id='sidebar_elements']/li[2]/p[2]/span[2]/text()")
    if len(video_info) == 0:
        video_info = html.xpath("//*[@id='sidebar_elements']/li[2]/p/span[1]/text()")
    video_mark = html.xpath("//*[@id='sidebar_elements']/li[3]/div/div[2]/span/span/@content")
    video_publisher = html.xpath("//*[@id='sidebar_elements']/li[5]/ul/li[1]/a/text()")
    # video_tag = html.xpath("")
    video_year = html.xpath("//*[@id='sidebar_elements']/li[4]/ul/li[3]/text()")
    # 获取剧集信息
    count = 1
    while True:
        rows = str(count)
        episode_number = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/span/text()")
        episode_img = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/img/@src")
        episode_url = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/@href")
        episode_name = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/img/@alt")
        if len(episode_number) == 0:
            break
        if len(episode_img) == 0:
            episode_img.append('null')
        # 保存图片
        episode_img[0] = save_image(name, episode_img[0])
        episode_name = str(episode_name[0]).replace(' ', '').replace(',', ' ').replace("\"", "\'")
        episode_insert(movie_id[0], episode_number[0].replace(' ', '').replace('/n', ''), episode_name, episode_img[0],
                       episode_url[0])
        count = count + 1
    if len(video_publisher) == 0:
        video_publisher.append('')
    if len(video_mark) == 0:
        video_mark.append(0)
    if len(video_info) == 0:
        video_info.append("null")
        print(video_info[0])
    return video_info[0], video_mark[0], video_publisher[0]


# 将剧集信息保存进入Mysql
def episode_insert(movie_id, episode_number, episode_name, episode_img, episode_url):
    db = pymysql.connect("localhost", "root", "root@cpx", "shows")
    cursor = db.cursor()
    sql = ' insert into episode(movie_id,episode_number,episode_name,episode_img,episode_url,download) values("%s","%s","%s","%s","%s",%s)' % \
          (movie_id, episode_number, episode_name, episode_img, episode_url, 0)
    try:
        cursor.execute(sql)
        db.commit()
    except:
        print('err:' + sql)
        db.rollback()
        raise
    db.close()


# 将动漫信息存入数据库
def movie_insert(movie_id, movie_name, img_url, movie_url, publisher, movie_mark, info, movie_type=0, movie_year=2020):
    db = pymysql.connect("localhost", "root", "root@cpx", "shows")
    cursor = db.cursor()
    info = info.replace("\"", "\'")
    movie_name.replace("\"", "\'")
    img_url = save_image(movie_name, img_url)
    sql = 'insert into movie values("%s","%s","%s","%s","%s","%s","%s","%s","%s")' % \
          (movie_id, movie_name, img_url, movie_url, publisher, movie_type, movie_mark, movie_year, info)
    try:
        cursor.execute(sql)
        db.commit()
        print("video_name " + str(movie_name) + " insert suecess")
    except:
        print("err:" + sql)
        db.rollback()
        raise
    db.close()


# 保存剧集图片到本地
def save_image(movie_name, image_url):
    try:
        if image_url.find("http") == -1:
            return ""
        image_path = "/Volumes/My Book/crunchyroll_image/" + movie_name
        data = requests.get(image_url)
        if not os.path.exists(image_path):
            os.mkdir(image_path)
        episode_path = str(uuid.uuid1()) + ".jpg"
        with open(image_path + "/" + episode_path, "wb") as f:
            f.write(data.content)
    except Exception as e:
        print(e)
        raise
    print("----下载成功------")
    episode_path = movie_name + "/" + episode_path
    return episode_path


if __name__ == "__main__":
    pool = ThreadPoolExecutor(5)
    print("begin")
    url = "https://www.crunchyroll.com/videos/anime/popular/ajax_page?pg="
    for page in range(0, 26):
        pool.submit(get_video_id, url, page)
        # get_video_id(url, page)
    print("end")
