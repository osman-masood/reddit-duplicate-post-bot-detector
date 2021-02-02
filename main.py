"""
Modified version of:
 https://github.com/impshum/Reddit-Duplicate-Comment-Remover

 Changes:
  - sleep_time variable name changed to run_frequency_minutes
  - More flexible regexp-based detection of duplicate comments
  - Minor code cleanup
  - Will use Counter class to detect offending bots, rather than lock/comments comments. Will only print out bot & comment names.
"""

from collections import Counter
from typing import Dict

import praw
import configparser
import re
import argparse
import schedule
from time import sleep

parser = argparse.ArgumentParser(
    description='Reddit Bot Detector (by u/notsohipsterithink)')
parser.add_argument(
    '-u', '--user', help='target individual user', type=str)
parser.add_argument(
    '-o', '--once', help='run only once', action='store_true')
args = parser.parse_args()

target_user, once_mode = False, False

if args.user:
    target_user = args.user

if args.once:
    once_mode = True

config = configparser.ConfigParser()
config.read('conf.ini')
reddit_user = config['REDDIT']['reddit_user']
reddit_pass = config['REDDIT']['reddit_pass']
client_id = config['REDDIT']['client_id']
client_secret = config['REDDIT']['client_secret']
target_subreddit = config['SETTINGS']['target_subreddit']
submission_limit = int(config['SETTINGS']['submission_limit'])
run_frequency_minutes = int(config['SETTINGS']['run_frequency_minutes'])
DUPLICATE_COMMENT_THRESHOLD = 5

reddit_client = praw.Reddit(client_id=client_id,
                            client_secret=client_secret,
                            username=reddit_user,
                            password=reddit_pass,
                            user_agent='Reddit Bot Detector (by u/notsohipsterithink)')

removed = ['[deleted]', '[removed]']


#
# class C:
#     W, G, R, Y = '\033[0m', '\033[92m', '\033[91m', '\033[93m'
#
#
# def remove_emoji(string):
#     emoji_pattern = re.compile('['
#                                u'\U0001F600-\U0001F64F'
#                                u'\U0001F300-\U0001F5FF'
#                                u'\U0001F680-\U0001F6FF'
#                                u'\U0001F1E0-\U0001F1FF'
#                                u'\U00002702-\U000027B0'
#                                u'\U000024C2-\U0001F251'
#                                ']+', flags=re.UNICODE)
#     return emoji_pattern.sub(r'', string)


def runner():
    author_to_comment_counter = dict()  # Maps username to Counter object. The Counter object counts cleaned comments.

    for submission in reddit_client.subreddit(target_subreddit).new(limit=submission_limit):
        # thread = {}
        # unique_comment_bodies = []
        # duplicate_comment_ids = []
        title = submission.title
        submission.comments.replace_more(limit=None)

        for comment in submission.comments.list():
            if should_skip_comment(comment):
                continue
            # comment_id = comment.id
            # created = comment.created_utc
            cleaned_body = clean_comment_body(comment.body)
            # body = remove_emoji(comment.body).replace(
            #     '*', '').replace(' ', '').replace('\n', '').lower()

            if not target_user or (target_user and target_user == comment.author.name):
                author_to_comment_counter.setdefault(comment.author.name, Counter())
                author_to_comment_counter[comment.author.name] += Counter({cleaned_body: 1})
                # thread.update({created: {'id': comment_id, 'body': body}})

        # for k, v in sorted(thread.items()):
        #     comment_id = v['id']
        #     body = v['body']
        #
        #     if body in unique_comment_bodies:
        #         duplicate_comment_ids.append(comment_id)
        #     else:
        #         unique_comment_bodies.append(body)
        #
        # if len(title) > 80:
        #     title = f'{title[0:80].strip()}...'
        #
        # print(f'{C.R}{len(duplicate_comment_ids)}{C.W}/{C.G}{len(unique_comment_bodies)} {C.W}{title}{C.W}')

        # Print detected bots within this subreddit.
        print(f'r/{target_subreddit}: Completed bot scanning of submission: {title}')
        print_bot_report(author_to_comment_counter)

        # for duplicate_comment_id in duplicate_comment_ids:
        #     comment = reddit.comment(duplicate_comment_id)
        # if not test_mode:

        # comment.mod.lock()
        # comment.mod.remove()
    print(f"r/{target_subreddit}: Completed bot scanning of most recent {submission_limit} submissions")
    print_bot_report(author_to_comment_counter)


def print_bot_report(author_to_comment_counter: Dict):
    for username, comment_counter in author_to_comment_counter.items():
        for cleaned_body, count in comment_counter.items():
            if count < DUPLICATE_COMMENT_THRESHOLD:
                continue
            print(f"Possible bot found: u/{username}: {cleaned_body} [Count = {count}]")


def clean_comment_body(comment_body):
    return re.sub(r'[^A-Za-z]', '', comment_body)


def should_skip_comment(comment):
    return not (comment.author and not comment.locked and comment.author not in removed and comment.body not in removed and
                len(comment.body) > 1)


def main():
    runner()
    if not once_mode:
        print(f"Schedule a run every {run_frequency_minutes} minutes")
        schedule.every(run_frequency_minutes).minutes.do(runner)
        while True:
            schedule.run_pending()
            sleep(1)


if __name__ == '__main__':
    main()
