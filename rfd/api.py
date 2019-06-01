"""RFD API."""

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError
import logging
from math import ceil
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

def get_posts(post, count=5, is_tail=False, per_page=40):
    """Retrieve posts from a thread.

    Args:
        post (str): either post id or full url
        count (int, optional): Description

    Yields:
        list(dict): body, score, and user
    """
    # print('get_posts(): post = %s, count = %d' % (post, count))

    post_id = __get_post_id(post)
    url = "{}/api/topics/{}/posts?per_page=40&page=1".format(API_BASE_URL, post_id)
    print('url = %s' % url)
    response = requests.get(url)
    pager = response.json().get("pager")
    total_posts = pager.get("total")
    total_pages = pager.get("total_pages")

    if count == 0:
        pages = total_pages
    if count > per_page:
        if count > total_posts:
            count = total_posts
        pages = ceil(count / per_page)
    else:
        if is_tail:
            pages = total_pages
        else:
            pages = 1

    if is_tail:
        start_page = ceil((total_posts + 1 - count) / per_page)
        start_post = (total_posts + 1 - count) % per_page
        if start_post == 0:
            start_post = per_page
    else:
        start_page, start_post = 0, 0

    # Go through as many pages as necessary
    results = []
    for page in range(start_page, pages + 1):
        response = requests.get(
            "{}/api/topics/{}/posts?per_page={}&page={}".format(
                API_BASE_URL, post_id, get_safe_per_page(per_page), page
            )
        )

        users = users_to_dict(response.json().get("users"))

        _posts = response.json().get("posts")

        # Determine which post to start with (for --tail)
        if page == start_page and not start_post == 0:
            if is_tail:
                _posts = _posts[start_post - 1 :]
            else:
                _posts = _posts[:start_post]

        print(len(_posts))
        for _post in _posts:
            # count -= 1
            # if count < 0:
            #     return results
            
            # Sometimes votes is null
            if _post.get("votes") is not None:
                calculated_score = calculate_score(_post)
            else:
                calculated_score = 0

            result = {
                "body": strip_html(_post.get("body")),
                "score": calculated_score,
                "user": users[_post.get("author_id")],
            }
            results.append(result)

    return results[:count]
