"""RFD API."""

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError
import logging
from math import ceil, floor
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from rfd.constants import API_BASE_URL


def build_web_path(slug):
    return "{}{}".format(API_BASE_URL, slug)


def extract_post_id(url):
    return url.split("/")[3].split("-")[-1]


def is_int(number):
    try:
        int(number)
        return True
    except ValueError:
        return False


def calculate_score(post):
    """Calculate either topic or post score. If votes cannot be retrieved, the score is 0.

    Arguments:
        post {dict} -- pass in the topic/post object

    Returns:
        int -- score
    """
    score = 0
    try:
        score = int(post.get("votes").get("total_up")) - int(
            post.get("votes").get("total_down")
        )
    except AttributeError:
        pass

    return score


def get_safe_per_page(limit):
    if limit < 5:
        return 5
    if limit > 40:
        return 40
    return limit


def users_to_dict(users):
    users_dict = {}
    for user in users:
        users_dict[user.get("user_id")] = user.get("username")
    return users_dict


def strip_html(text):
    return BeautifulSoup(text, "html.parser").get_text()


def is_valid_url(url):
    result = urlparse(url)
    return all([result.scheme, result.netloc, result.path])


def get_threads(forum_id, limit):
    """Get threads from rfd api

    Arguments:
        forum_id {int} -- forum id
        limit {[type]} -- limit number of threads returned

    Returns:
        dict -- api response
    """
    try:
        response = requests.get(
            "{}/api/topics?forum_id={}&per_page={}".format(
                API_BASE_URL, forum_id, get_safe_per_page(limit)
            )
        )
        if response.status_code == 200:
            return response.json()
        logging.error("Unable to retrieve threads. %s", response.text)
    except JSONDecodeError as err:
        logging.error("Unable to retrieve threads. %s", err)
    return None


def parse_threads(api_response, limit):
    """parse topics list api response into digestible list.

    Arguments:
        api_response {dict} -- topics response from rfd api
        limit {int} -- limit number of threads returned

    Returns:
        list(dict) -- digestible list of threads
    """
    threads = []
    if api_response is None:
        return threads
    for topic in api_response.get("topics"):
        threads.append(
            {
                "title": topic.get("title"),
                "score": calculate_score(topic),
                "url": build_web_path(topic.get("web_path")),
            }
        )
    return threads[:limit]


def __get_post_id(post):
    if is_valid_url(post):
        return extract_post_id(post)
    elif is_int(post):
        return post
    else:
        raise ValueError()


def get_posts(post, start, count, per_page=40):
    """Retrieve posts from a thread.
    """
    print(start, count)

    total_pages, total_posts = find_totals(__get_post_id(post))
    print(total_pages, total_posts)

    if count == 0:
        count = total_posts - start
    elif start + count > total_posts:
        count = total_posts - start

    start_page = ceil(start / per_page)
    page_count = min(total_pages, (start + count) / per_page)

    # Go through as many pages as necessary
    results = []
    for page in range(start_page, start_page + page_count):
        post_id = __get_post_id(post)
        response = requests.get(
            "{}/api/topics/{}/posts?per_page={}&page={}".format(
                API_BASE_URL, post_id, get_safe_per_page(per_page), page
            )
        )

        users = users_to_dict(response.json().get("users"))
        _posts = response.json().get("posts")

        print(len(_posts))
        for _post in _posts:
            # Sometimes votes is null
            calculated_score = 0 if _post.get(
                "votes") is None else calculate_score(_post)

            result = {
                "body": strip_html(_post.get("body")),
                "score": calculated_score,
                "user": users[_post.get("author_id")],
            }
            results.append(result)

    return results[:count]


def find_totals(post_id):
    url = "{}/api/topics/{}/posts?per_page=40&page=1".format(
        API_BASE_URL, post_id)
    # print('url = %s' % url)
    response = requests.get(url)
    pager = response.json().get("pager")
    total_posts = pager.get("total")
    total_pages = pager.get("total_pages")
    return total_pages, total_posts
