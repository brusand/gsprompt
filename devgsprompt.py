#!/usr/bin/env python
from __future__ import unicode_literals
import asyncio
import array
import unicodedata
import argparse
import requests
import pyquery
import json
import sys
import time
import csv
import threading
from configobj import ConfigObj
import numpy as np
from time import sleep
from datetime import datetime, time, timedelta
from influxdb import InfluxDBClient
from configobj import ConfigObj
from time import strptime

from prompt_toolkit import PromptSession
from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.history import FileHistory
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop

host = 'localhost'
#host = '35.184.211.204'
port = '8086'
user = 'admin'
password = ''
json_rank_body = [
    {
        "measurement": str(''),
        "tags": {
            "user": str(''),
            "photo": str('')
        },
        "time": str(''),
        "fields": {
            "player": str(''),
            "rank": 0,
            "votes": 0,
            "gp": False
        }
    }
 ]
json_audience_body = [
    {
        "measurement": str(''),
        "tags": {
            "challenge": str('')
        },
        "time": str(''),
        "fields": {
            "players": 0,
            "votes": 0,
            "total_votes": float(0),
            "delta_votes": float(0)
        }
    }
 ]

def datetime_to_utc_milliseconds(aDateTime):
    return int(calendar.timegm(aDateTime.timetuple())*1000)

class GuruBatch():
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='challenge')
        self.parser.add_argument('--player', nargs='?', help='Player', default='')
        self.parser.add_argument('--xtoken', help='xtoken', required=False)
        self.parser.add_argument('--cmde', nargs='?', help='Cmde', default='')
        self.parser.add_argument('--shell ', action="store_true", default=False)
        self.subparsers = self.parser.add_subparsers(dest='cmd', help='sub-command help')

        self.parser_fill = self.subparsers.add_parser('fill')
        self.parser_fill.add_argument('fill', type=int, action="store", default=0)
        self.parser_fill.add_argument('--at', nargs='?', help='time', default='')
        self.parser_fill.add_argument('--left', nargs='?', help='time left', default='')
        self.parser_fill.add_argument('--above', nargs='?', help='above', default='')
        self.parser_fill.add_argument('--cha', nargs='?', help='above', default='')
        self.parser_fill.add_argument('--player', nargs='?', help='player', default='')
        self.parser_fill.set_defaults(func=self.fill)

        self.parser_vote = self.subparsers.add_parser('vote')
        self.parser_vote.add_argument('vote', type=int, action="store", default=0)
        self.parser_vote.add_argument('--at', nargs='?', help='time', default='now')
        self.parser_vote.set_defaults(func=self.vote)

        self.parser_prompt = self.subparsers.add_parser('prompt')
        self.parser_prompt.add_argument('prompt', action="store", default='')
        self.parser_prompt.set_defaults(func=self.prompt)

        self.parser_ps = self.subparsers.add_parser('ps')
        self.parser_ps.add_argument('ps', nargs='?', action="store", default='')
        self.parser_ps.add_argument('--list', action="store_true", default=False)
        self.parser_ps.add_argument('--pop', nargs='?', action="store", default='')
        self.parser_ps.set_defaults(func=self.ps)

        self.parser_bye = self.subparsers.add_parser('bye')
        self.parser_bye.set_defaults(func=self.bye)

        self.parser_challenge = self.subparsers.add_parser('challenge')
        self.parser_challenge.add_argument('challenge', nargs='?', action='store', help='challenge', default='')
        self.parser_challenge.add_argument('--fill', nargs='?', type=int, action="store", default=0)
        self.parser_challenge.add_argument('--add', action="store_true", default=False)
        self.parser_challenge.add_argument('--log', action="store_true", default=False)
        self.parser_challenge.add_argument('--at', nargs='?', action="store", default='')
        self.parser_challenge.add_argument('--left', nargs='?', action="store", default='')
        self.parser_challenge.add_argument('--vote', nargs='?', type=int, action="store", default=0)
        self.parser_challenge.add_argument('--list', action="store_true", default=False)
        self.parser_challenge.add_argument('--last', action="store_true", default=False)
        self.parser_challenge.add_argument('--all', action="store_true", default=False)
        self.parser_challenge.add_argument('--display', action="store_true", default=False)
        self.parser_challenge.add_argument('--replay', action="store_true", default=False)
        self.parser_challenge.add_argument('--update', action="store_true", default=False)
        self.parser_challenge.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_challenge.set_defaults(func=self.challenge)

        self.parser_audience = self.subparsers.add_parser('audience')
        self.parser_audience.add_argument('audience', nargs='?', action="store", default='*')
        self.parser_audience.add_argument('--at', nargs='?', help='time', default='')
        self.parser_audience.add_argument('--left', nargs='?', help='time left', default='')
        self.parser_audience.add_argument('--list', action="store_true", default=True)
        self.parser_audience.add_argument('--open', action="store_true", default=True)
        self.parser_audience.add_argument('--start', action="store_true", default=False)
        self.parser_audience.add_argument('--stop', action="store_true", default=False)
        self.parser_audience.add_argument('--add', action="store_true", default=False)
        self.parser_audience.add_argument('--delay', nargs='?', type=int, action="store", default=5)
        self.parser_audience.set_defaults(func=self.audience)

        self.parser_fill = self.subparsers.add_parser('fill')
        self.parser_fill.add_argument('fill', nargs='?', action="store", default='*')
        self.parser_fill.add_argument('--list', action="store_true", default=False)
        self.parser_fill.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_fill.add_argument('--player', nargs='?', action="store", default='')
        self.parser_fill.add_argument('--all', action="store_true", default=False)
        self.parser_fill.add_argument('--at', nargs='?', action="store", default='')
        self.parser_fill.add_argument('--left', nargs='?', action="store", default='')
        self.parser_fill.add_argument('--above', action="store_true", default=True)
        self.parser_fill.set_defaults(func=self.fill)

        self.parser_vote = self.subparsers.add_parser('vote')
        self.parser_vote.add_argument('vote', nargs='?', action="store", default='1')
        self.parser_vote.add_argument('--list', action="store_true", default=False)
        self.parser_vote.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--player', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--all', action="store_true", default=False)
        self.parser_vote.add_argument('--at', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--left', nargs='?', action="store", default='')
        self.parser_vote.add_argument('--photo', nargs='?', action="store", default='')
        self.parser_vote.set_defaults(func=self.vote)

        self.parser_member = self.subparsers.add_parser('member')
        self.parser_member.add_argument('member', nargs='?', action="store", default='*')
        self.parser_member.add_argument('--list', action="store_true", default=False)
        self.parser_member.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_member.add_argument('--watch', nargs='?', action="store", default='')
        self.parser_member.add_argument('--photo', nargs='?', action="store", default='')
        self.parser_member.add_argument('--at', nargs='?', action="store", default='')
        self.parser_member.add_argument('--left', nargs='?', action="store", default='')
        self.parser_member.add_argument('--vote', action="store_true", default=False)
        self.parser_member.add_argument('--stop', action="store_true", default=False)
        self.parser_member.add_argument('--limit', nargs='?', type=int, action="store", default=200)
        self.parser_member.add_argument('--start', nargs='?', type=int, action="store", default=0)
        self.parser_member.add_argument('--nb', nargs='?', type=int, action="store", default=1)
        self.parser_member.set_defaults(func=self.member)

        self.parser_log = self.subparsers.add_parser('log')
        self.parser_log.add_argument('log', nargs='?', action="store", default='.')
        self.parser_log.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_log.add_argument('--all', action="store_true", default=False)
        self.parser_log.add_argument('--at', nargs='?', action="store", default='')
        self.parser_log.add_argument('--left', nargs='?', action="store", default='')
        self.parser_log.set_defaults(func=self.log)

        self.parser_swap = self.subparsers.add_parser('swap')
        self.parser_swap.add_argument('swap', nargs='?', action="store", default='1')
        self.parser_swap.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_swap.add_argument('--by', nargs='?', action="store", default='')
        self.parser_swap.add_argument('--at', nargs='?', action="store", default='')
        self.parser_swap.add_argument('--left', nargs='?', action="store", default='')
        self.parser_swap.set_defaults(func=self.swap)

        self.parser_unlock = self.subparsers.add_parser('unlock')
        self.parser_unlock.add_argument('unlock', nargs='?', action="store", default='')
        self.parser_unlock.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_unlock.add_argument('--at', nargs='?', action="store", default='')
        self.parser_unlock.add_argument('--left', nargs='?', action="store", default='')
        self.parser_unlock.add_argument('--boost', action="store_true", default=False)
        self.parser_unlock.set_defaults(func=self.unlock)

        self.parser_boost = self.subparsers.add_parser('boost')
        self.parser_boost.add_argument('boost', nargs='?', action="store", default='')
        self.parser_boost.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_boost.add_argument('--at', nargs='?', action="store", default='')
        self.parser_boost.add_argument('--left', nargs='?', action="store", default='')
        self.parser_boost.set_defaults(func=self.boost)

        self.parser_submit = self.subparsers.add_parser('submit')
        self.parser_submit.add_argument('submit', nargs='?', action="store", default='')
        self.parser_submit.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_submit.add_argument('--at', nargs='?', action="store", default='')
        self.parser_submit.add_argument('--left', nargs='?', action="store", default='')
        self.parser_submit.set_defaults(func=self.submit)


        self.parser_strategie = self.subparsers.add_parser('strategie')
        self.parser_strategie.add_argument('strategie', nargs='?', action="store", default='*')
        self.parser_strategie.add_argument('--cha', nargs='?', action="store", default='')
        self.parser_strategie.add_argument('--player', nargs='?', action="store", default='')
        self.parser_strategie.add_argument('--list', action="store_true", default=False)
        self.parser_strategie.add_argument('--start', action="store_true", default=False)
        self.parser_strategie.add_argument('--stop', action="store_true", default=False)
        self.parser_strategie.add_argument('--step', nargs='?', action="store", default='1')
        self.parser_strategie.add_argument('--at', nargs='?', action="store", default='')
        self.parser_strategie.add_argument('--left', nargs='?', action="store", default='')
        self.parser_strategie.set_defaults(func=self.strategie)

        self.parser_ranking = self.subparsers.add_parser('ranking')
        self.parser_ranking.add_argument('audience', nargs='?', action="store", default='*')
        self.parser_ranking.add_argument('--list', action="store_true", default=False)
        self.parser_ranking.add_argument('--start', action="store_true", default=False)
        self.parser_ranking.add_argument('--stop', action="store_true", default=False)
        self.parser_ranking.add_argument('--add', action="store_true", default=False)
        self.parser_ranking.set_defaults(func=self.ranking)

        self.parser_player = self.subparsers.add_parser('player')
        self.parser_player.add_argument('player', nargs='?', action="store", default='')
        self.parser_player.add_argument('--list', action="store_true", default=False)
        self.parser_player.add_argument('--add', action="store_true", default=False)
        self.parser_player.add_argument('--set', action="store_true", default=False)
        self.parser_player.set_defaults(func=self.players)

        self.parser_ps = self.subparsers.add_parser('ps')
        self.parser_ps.add_argument('ps', nargs='?', action="store", default='')
        self.parser_ps.add_argument('--list', action="store_true", default=False)
        self.parser_ps.add_argument('--stop', action="store_true", default=False)
        self.parser_ps.add_argument('--restart', action="store_true", default=False)
        self.parser_ps.add_argument('--pop', nargs='?', action="store", default='')
        self.parser_ps.add_argument('--purge', action="store_true", default=False)
        self.parser_ps.set_defaults(func=self.ps)

        self.parser_prompt = self.subparsers.add_parser('prompt')
        self.parser_prompt.add_argument('prompt', action="store_true", default='False')
        self.parser_prompt.set_defaults(func=self.prompt)




        self.members = {}
        self.watchings = {}

        self.config = ConfigObj('devgurushot.ini')
        if self.config.get('players') == None:
            self.config['players'] = {}

        self.config.write()

        self.strategies = ConfigObj('devvostrategies.ini')

    def init(self, args):
        if not args.player:
           self.player = ''
        else:
            if self.config['players'].get(args.player) == None:
                self.config['players'][args.player] = {}
                self.config['players'][args.player]['last_challenge'] = ''
                self.config['players'][args.player]['xtoken'] = ''

            if args.xtoken is not  None:
                self.config['players'][args.player]['xtoken'] = args.xtoken

            self.player = args.player
            self.config['player'] = args.player
            self.config.write()

        self.xtoken = self.config['players'][args.player]['xtoken']
        self.connect()
        self.challenges = ConfigObj('challenges-'+ self.player + '.ini')

        self.bye = False

        self.init_process(args)


    def init_process(self, args):

        try:
            self.purge_challenge()
            challenges = self.get_joined_challenges()
            challenges_open = self.get_open_challenges()
            challenges["challenges"].extend(challenges_open["items"])

            for challenge in challenges["challenges"]:
                    if self.challenges.get(challenge['url']) == None:
                        self.add_challenge(challenge)
                        self.log_challenge(challenge)

            self.ps_restart(args)
        except Exception as _error:
            print('error',  _error)
    def purge_challenge(self):
        #move closed challenge
        for section in self.challenges.keys():
            if datetime.now() > datetime.strptime(self.challenges[section]['end'], "%d/%m/%Y, %H:%M"):
                self.challenges.pop(section)
                print('challenge', section, 'popped')

    def add_challenge(self, challenge):
        url = challenge["url"]
        self.challenge_details = self.get_challenge(url)

        if self.challenges.get(url) == None:
            self.challenges[url] = {}
            self.challenges[url]['title'] = challenge["title"]
            self.challenges[url]['strategie'] = ''
            self.challenges[url]['audience'] = False
            self.challenges[url]['last_votes'] = 0
            self.challenges[url]['ranking'] = False
            self.challenges[url]['score'] = False
            self.challenges[url]['step'] = 0



        #if self.challenge_details["items"]["challenge"]["close_time"] != 0:
            #vote_data = self.get_votes_panel(self.challenge_details["items"]["challenge"]["url"])
            #self.challenges[url]['jauge']  = str(vote_data["voting"]["exposure"]["exposure_factor"])

        self.challenges[url]['challenge_votes'] = self.challenge_details["items"]["challenge"]["votes"]
        self.challenges[url]['challenge_players'] = self.challenge_details["items"]["challenge"]["players"]
        self.challenges[url]['rank'] = "-1" #str(challenge["member"]["ranking"]["total"]["rank"])
        #self.challenges[url]['votes'] =  "-1" #str(challenge["member"]["ranking"]["total"]["votes"])
        #self.list.SetItem(self.index, 4, f"{self.challenge_details["items"]["challenge"]["time_left"]["days"]}D {self.challenge_details["items"]["challenge"]["time_left"]["hours"]}:{self.challenge_details["items"]["challenge"]["time_left"]["minutes"]}:{self.challenge_details["items"]["challenge"]["time_left"]["secondss"]}"
        timeleft = self.challenge_details["items"]["challenge"]["time_left"];
        self.challenges[url]['timeleft'] = "{}D {}H {}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"])
        self.challenges[url]['end'] = datetime.fromtimestamp(self.challenge_details["items"]["challenge"]["close_time"]).strftime("%d/%m/%Y, %H:%M")
        self.challenges.write()

    def get_votes_panel(self,  url):
        # get vote_ data
        response_panel = self.session.post('https://gurushots.com/rest/get_vote_data', data={
            'limit': 100,
            'url': url
        })
        content_panel = response_panel.content
        return json.loads(content_panel)

    def get_joined_challenges(self):
        response = self.session.post('https://gurushots.com/rest/get_member_joined_active_challenges')
        content = response.content
        return json.loads(content)

    def get_open_challenges(self):
        response = self.session.post('https://gurushots.com/rest/get_member_challenges', data={
            'filter': 'open'
        })
        content = response.content
        return json.loads(content)

    def ps(self, args):
        for section in self.challenges.keys():
            if (args.cha == '*') or (args.cha == section):
                print (section, ' strategie ', self.challenges[section]['strategie'], ' step ', self.challenges[section][
                    'step'], ' ThreadId ', self.challenges[section]['threadId'])

    def action(self, args):
        for section in self.challenges.keys():
            if (args.cha == '*') or (args.cha == section):
                self.action_exec(section, args)

    def fill(self, args):
        for section in self.challenges.keys():
                self.fill_exec(section, args)

    def vote(self, args):
        for section in self.challenges.keys():
                self.vote_exec(section, args)

    def action_thread_args(self, challenge, action, value, args):
       process_id = challenge + '-' + action + '-' + str(value) + '-'
       if args.at:
           at_split = args.at.split(':')
           at_day = datetime.now() + timedelta(days=int(at_split[0]))
           at_time = datetime(at_day.year, at_day.month, at_day.day, int(at_split[1]), int(at_split[2]), 0)
           process_id += 'at-'+at_time.strftime('%Y-%m-%d_%H:%M')
       else:
           if args.left:
               left_delta = args.left.split(':')
               process_id += 'left-'+"{}H:{}M".format(left_delta[0], left_delta[1])
           else:
                process_id += datetime.now().strftime('%Y-%m-%d_%H:%M')

       process_state = 'init'
       self.ps_add(process_id, process_state, action, value, args)

#       print "new process ", challenge['title'], ' action ', action, ' value ', value, ' at ', at, ' left ', left
       waiting_time = False
       exec_action = True
       try:
           if args.at:
                #print "at ", at
                at_now = datetime.now()
                if at_now > at_time:
                    exec_action = False
                    raise('too late')
                else:
                    self.ps_update(process_id, 'waiting')

                    while  datetime.now() <= at_time:
                        sleep(60)
                        if self.config['players'][self.player]['process'][process_id] = 'stop':
                            self.ps_update(process_id, 'stopped')
                            return
           if args.left:
                challenge_details = self.get_challenge(challenge)
                timeleft = challenge_details["items"]["challenge"]["time_left"];
                timeLeftString = str("{}D:{}H:{}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"]))
                if timedelta(hours=int(timeleft['hours']),
                             minutes=int(timeleft['minutes'])) > timedelta( hours=int(left_delta[0]),
                                                                            minutes=int(left_delta[1])):
                    self.ps_update(process_id, 'waiting')
                    waiting_time = True
                    while  waiting_time:
                        try:
                            if self.config['players'][self.player]['process'][process_id] = 'stop':
                                self.ps_update(process_id, 'stopped')
                                return
                            sleep(60)
                            challenge_details = self.get_challenge(challenge)
                            timeleft = challenge_details["items"]["challenge"]["time_left"];
                            timeLeftString = str("{}D:{}H:{}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"]))
                            #print "timeleft ", timeLeftString
                            if  timedelta(hours=int(timeleft['hours']), minutes=int(timeleft['minutes'])) <= timedelta(hours=int(left_delta[0]), minutes=int(left_delta[1])):
                                waiting_time = False
                        except (RuntimeError, TypeError, NameError):
                            sleep(30)
                            pass
           self.ps_update(process_id, 'executing')

           if exec_action:
               if action in "fill":
                   self.fill_challenge(challenge, value)
               if action in "vote":
                   if args.photo is not '':
                       self.vote_photo(challenge, votes, args.photo)
                   else:
                        self.vote_challenge(challenge, value)
               if action in "log":
                   self.log_action(challenge, "log", value, args)
               if action == "boost":
                   print ('exec : ' + 'BOOST')
               if action == "post":
                   print ('exec : ' + 'POST')
               if action in "submit":
                   self.submit_challenge(challenge, value, args)
               if action in "unlock":
                   self.unlock_challenge(challenge, value, args)
               if action in "boost":
                   self.boost_challenge(challenge, value, args)

               if action in "swap":
                       self.swap_challenge(challenge, value, args)
               if action in "photo":
                   self.member_vote_photo_id(challenge, value, args)

               if action in "member":
                       self.member_vote_challenge_member_id(challenge, value, args)
               if action in "watch":
                       self.watch_challenge_member_id(challenge, value, args)
               if action in "audience":
                       self.audience_thread()
               if action == "jauge":
                   print ('exec : ' + 'JAUGE')

               if action == "AT":
                   print ('exec : ' + 'AT')


           self.ps_update(process_id, 'success')

#       except (RuntimeError, TypeError, NameError):
       except Exception as _error:
            print(_error)
            self.ps_update(process_id, 'error')
            pass

    def action_exec_args(self, challenge, action, value, args):
        self.execThread = threading.Thread(target=self.action_thread_args, name=challenge+action+str(value), kwargs=dict(challenge=challenge, action=action, value=str(value), args=args))
        self.execThread.daemon = True  # Daemonize thread
        self.execThread.start()


    def displayChallenge(self, challenge, args):
        challengeUrl = challenge

        self.challenge_details = self.get_challenge(challengeUrl)
        name = self.challenge_details["items"]["challenge"]["title"]

        timeleft = self.challenge_details["items"]["challenge"]["time_left"];
        timeLeft = "{}D {}H {}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"])
        timeEnd  = datetime.fromtimestamp(self.challenge_details["items"]["challenge"]["close_time"]).strftime(
                    "%d/%m/%Y, %H:%M")

        if not args.all:
            if (timeleft["days"] != 0 or timeleft["hours"] != 0 and  timeleft["minutes"] != 0 or timeleft["seconds"] != 0) and (self.challenge_details["items"]["challenge"]["member"]['is_joined'] == True):
                try:
                    vote_data = self.get_votes_panel(self.challenge_details["items"]["challenge"]["url"])
                    jauge = ''
                    vote_exposure_factor = ''
                    rank = ''
                    vote = ''
                    total_votes =  self.challenge_details["items"]["challenge"]["votes"]
                    total_players = self.challenge_details["items"]["challenge"]["players"]
                    timeleft = self.challenge_details["items"]["challenge"]["time_left"];
                    timeLeftString = str("{}D:{}H:{}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"]))
                    timeEnd = datetime.fromtimestamp(self.challenge_details["items"]["challenge"]["close_time"]).strftime("%d/%m/%Y, %H:%M")

                    jauge = vote_data["voting"]["exposure"]["exposure_factor"]
                    vote_exposure_factor = vote_data["voting"]["exposure"]["vote_exposure_factor"]
                        #rank = challenge["member"]["ranking"]["total"]["rank"]
                        #votes =  challenge["member"]["ranking"]["total"]["votes"]

                    print ('challenge : ', name, '(', challenge, ')', 'jauge', jauge, 'vote_exposure', vote_exposure_factor, 'time-left', timeLeftString, 'end at', timeEnd, 'total votes', total_votes, 'total_players', total_players)

                except Exception as _error:
                    print (challenge, _error)
            else:
                print (challenge, "Closed")
        else:
            print ('challenge : ', name, '(', challenge[
                "url"], ')', 'time-left', timeLeft, 'end at', timeEnd, 'votes')

    def post_votes( self, challenge_details, votes):
        if self.session:
            try:
                payload = {'image_ids['+str(id)+']': value for id, value in enumerate(votes)}
                payload['c_id'] = challenge_details["items"]["challenge"]["id"]
                response = self.session.post('https://gurushots.com/rest/submit_votes', data=payload)
                content = response.content
                return json.loads(content)
            except Exception as _error:
                print(_error)
                return ''


    def member_vote_photo_id(self, challenge, photo, args):
        challenge_details = self.get_challenge(challenge)
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            votes_panel = []
            print(args.photo.encode('utf-8'))
            photo_id = args.photo
            photo_id_u = u"fee36ce85e56ded46a7b1f770d169ee1"
            photo_id_unicode = args.photo.encode()
            print(photo_id, photo_id_u, photo_id_unicode)
            votes_panel.append('u', photo_id_u)
            #votes_panel.append('u', photo_id_u)
            self.post_votes(challenge_details, votes_panel)
            #self.post_votes(challenge_details, votes_panel)
            self.log_action(challenge, "photo", str(len(votes_panel)))

    def vote_challenge(self, challenge, votes):
        challenge_details = self.get_challenge(challenge)
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            vote_count_max = int(votes)
            vote_count = 0
            vote_index = 0
            votes_panel = []
            vote_data = self.get_votes_panel(challenge)
            while vote_count < vote_count_max and vote_index < len(vote_data["images"]):
                vote_image = vote_data["images"][vote_index]
                # si non reported

                if vote_image["width"] < 1080:
                    votes_panel.append(vote_image["id"])
                    vote_count = vote_count + 1

                vote_index = vote_index + 1

                if vote_index == len(vote_data["images"]):
                    self.post_votes(challenge_details, votes_panel)
                    vote_data = self.get_votes_panel(challenge)
                    vote_index = 0
                    votes_panel = []
            self.post_votes(challenge_details, votes_panel)
            self.log_action(challenge, "vote" , str(votes))

    def member_vote_challenge_member_id(self, challenge, member_id, args):
        challenge_details = self.get_challenge(challenge)
        vote_page = 0
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            vote_index = 0
            votes = []
            vote_data = self.get_votes_panel(challenge)
            vote_page = 0
            nb = 1
            while vote_data and self.members[member_id]['stop'] == False:
                print (challenge, "member voting", nb, args.member, vote_page)
                for image in vote_data["images"]:
                    if image["member_id"] == member_id:
                        votes.append(image["id"])
                        self.post_votes(challenge_details, votes)
                        print (challenge, "member voted", nb, args.member, vote_page)
                        nb = nb + 1
                        #self.log_action(challenge, "member voted", member_id)
                        if nb > args.nb:
                            return
                vote_index = 0
                votes = []
                sleep(1)
                vote_data = self.get_votes_panel(challenge)
                vote_page = vote_page + 1

            if self.members[member_id] == True:
                self.log_action(challenge, "member vote aborted", member_id)




    def watch_challenge_member_id(self, challenge, member_id, args):
        # get followings photos
        # if none photo : none
        # if prec none :  image :> submit
        # if prec im : swap


        if self.watchings[''] == False:
            while self.watchings[member_id]['stop'] == False:
                try:
                    #followings_photos = self.get_followings_photos(challenge)
                    sleep(60)
                except (RuntimeError, TypeError, NameError):
                    sleep(30)
                    pass




    def log_action(self, url,  lib, value):
        return
        challenge_details = self.get_challenge(url)

        if self.challenges[url].get('log') == None:
             self.challenges[url]['log'] = {}

        timeleft = challenge_details["items"]["challenge"]["time_left"];
        timeLeftString = "{}D{}H{}M{}S".format(timeleft["days"], timeleft["hours"], timeleft["minutes"],
                                               timeleft["seconds"])
        if self.challenges[url]['log'].get(timeLeftString) == None:
            self.challenges[url]['log'][timeLeftString] = {}
        self.challenges[url]['log'][timeLeftString][lib] = value
        #rank = challenge['member']['ranking']['total']['rank']
        rank = -1
        self.challenges[url]['rank'] = rank

        #vote_data = self.get_votes_panel(url)
        #jauge = str(vote_data["voting"]["exposure"]["exposure_factor"])

        #vote_exposure_factor = str(vote_data["voting"]["exposure"]["vote_exposure_factor"])
        #self.challenges[url]['jauge'] = jauge
        #self.challenges[url]['vote_exposure_factor'] = vote_exposure_factor
        #boost =  challenge['boost_state']
        boost = False
        self.challenges[url]['boost'] = boost
        votes =  challenge_details["items"]["challenge"]["votes"]
        self.challenges[url]['votes'] = votes
        players = challenge_details["items"]["challenge"]["players"]
        self.challenges[url]['players'] = players
        #fill_discount = challenge_details["items"]["settings"]['fill_discount_min']
        #self.challenges[url]['fill_discount'] = fill_discount

        self.challenges.write()
        #print timeLeftString, ' ', challenge_details["items"]["challenge"]['title'], ' jauge ', jauge, lib, " ", value, ' rank ', rank, ' vote_exposor_factor ', vote_exposure_factor, ' fill_discount ', fill_discount, ' votes ', votes, ' players ', players
        print (timeLeftString, ' ', challenge_details["items"]["challenge"]['title'], ' votes ', votes, ' players ', players)

    def fill_challenge(self, challenge, fill):
        challenge_details = self.get_challenge(challenge)
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            vote_data = self.get_votes_panel(challenge)
            print('Filling ' + challenge_details["items"]["challenge"]["title"] + ' exposure : ' + str(vote_data["voting"]["exposure"]["exposure_factor"]))
            if (vote_data["voting"]["exposure"]["exposure_factor"] < int(fill)):
                vote_count_max = int(fill) - int(vote_data["voting"]["exposure"]["exposure_factor"])
                self.vote_challenge(challenge, vote_count_max)


    def swap_challenge(self, challenge, swap, args):
        challenge_details = self.get_challenge(challenge)
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            self.swap_photo(challenge_details["items"]["challenge"]["id"], swap, args.by)

    def boost_challenge(self, challenge, photo_id, args):
        challenge_details = self.get_challenge(challenge)
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            self.boost_photo(challenge_details["items"]["challenge"]["id"], photo_id)

    def submit_challenge(self, challenge, submit, args):
        challenge_details = self.get_challenge(challenge)
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            self.submit_to_challenge(challenge_details["items"]["challenge"]["id"], submit)

    def unlock_challenge(self, challenge, unlock, args):
        challenge_details = self.get_challenge(challenge)
        if challenge_details["items"]["challenge"]["close_time"] != 0:
            self.unlock_key(challenge_details["items"]["challenge"]["id"], args.boost)


    def log_challenge(self, challenge):
        print ('log')
#        challenge_details = self.get_challenge(challenge["url"])
#        if challenge_details["items"]["challenge"]["close_time"] != 0:
#           self.log_action(challenge, "log", '')

    def load_challenges(self, args):
        challenges = self.get_joined_challenges()
        if args.all:
            challenges_open = self.get_open_challenges()
#            for challenge in challenges_open["items"]:
            challenges["challenges"].extend(challenges_open["items"])
        return challenges

    def challenge(self, args):
        args.challenge.replace('_','-')
        if args.update:
            challenges = self.load_challenges(args)

        if args.list:
            for section in self.challenges.keys():
                if args.challenge in '*' or args.challenge in section:
                    self.displayChallenge(section, args)


    def audience_add(self, challenge, args):
        print ('audience ' + self.challenges[challenge]['title'])
        self.challenges[challenge]['audience'] = True
        #self.challenges[challenge['url']]['audience_delay'] = args.delay
        self.challenges.write()

    def convert_si_to_number(self, x):
        total_stars = 0
        if 'K' in x:
            if len(x) > 1:
                total_stars = float(x.replace('K', '')) * 1000  # convert k to a thousand
        elif 'M' in x:
            if len(x) > 1:
                total_stars = float(x.replace('M', '')) * 1000000  # convert M to a million
        elif 'B' in x:
            total_stars = float(x.replace('B', '')) * 1000000000  # convert B to a Billion
        else:
            total_stars = int(x)  # Less than 1000

        return float(total_stars)

    def audience_thread(self):
        print ("new process ", 'audience')

        stillOpen = True

        if  self.config['players'][self.player].get('host') == None:
            host = 'localhost'
        else:
            host = self.config['players'][self.player]['host']


        if  self.config['players'][self.player].get('port') == None:
            port = '8086'
        else:
            port = self.config['players'][self.player]['port']

        if  self.config['players'][self.player].get('user') == None:
            user = 'admin'
        else:
            user = self.config['players'][self.player]['user']

        client = InfluxDBClient(host, port, user, password, "gurus")
        self.stillAudienceRunning = True

        while self.stillAudienceRunning:
            for section in self.challenges.keys():
                if self.challenges.get(section).as_bool('audience'):
                    #print "Thread audience : ", section
                    challenge_details = self.get_challenge(section);
                    timeleft = challenge_details["items"]["challenge"]["time_left"]
                    if timeleft["days"] == 0 and  timeleft["hours"]  == 0 and  timeleft["minutes"] == 0 and timeleft["seconds"] == 0:
                        print ('Thread audience ', section, ' termine')
                        self.challenges[section]['audience'] = False
                        self.challenges.write()
                    else:
                        with open('audience_' + section + '_file.csv', mode='a') as audience_file:
                            audience_writer = csv.writer(audience_file, delimiter=',', quotechar='"',
                                                         quoting=csv.QUOTE_MINIMAL)

                            last_votes = self.challenges[section]['last_votes']
                            audience = json_audience_body
                            audience[0]['measurement'] = 'audiences1'
                            audience[0]["tags"]['challenge'] = section
                            audience[0]["fields"]['total_votes'] = self.convert_si_to_number(challenge_details["items"]["challenge"]["votes"])
                            audience[0]["fields"]['delta_votes'] = self.convert_si_to_number(challenge_details["items"]["challenge"]["votes"]) - self.convert_si_to_number(last_votes)
                            audience[0]["fields"]['players'] = challenge_details["items"]["challenge"]["players"]
                            audience[0]["time"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                            timeLeftString = str(
                                "{}D:{}H:{}M".format(timeleft["days"], timeleft["hours"], timeleft["minutes"]))
                            print ('audience ',  audience[0]["tags"]['challenge'], 'votes', audience[0]["fields"]['total_votes'] ,  ' ecart votes' ,  str(audience[0]["fields"]['delta_votes']))
                            audience_writer.writerow([audience[0]["time"], timeLeftString, audience[0]["fields"]['total_votes'], audience[0]["fields"]['delta_votes'], audience[0]["fields"]['players']])

                            last_votes = challenge_details["items"]["challenge"]["votes"]
                            self.challenges[section]['last_votes'] = last_votes
                            self.challenges.write()
                            #if client is not None:
                                # out = store_record(es, 'ranks', 'rank', doc)
                                #print ('audience ', section, ' ecart votes' ,  str(audience[0]["fields"]['delta']))
                                #client.write_points(audience)
            sleep(5*60)
        #print" ended", 'Audience'

    def audience_start(self, args):
        if self.player in 'audience':
            self.action_exec_args("audience", "audience", '', args)
        else:
            print ('only audience player could start')

    def audience_stop(self, args):
        self.stillAudienceRunning = False

    def audience(self, args):
        challenges = self.get_joined_challenges()
        if args.start:
            self.audience_start(args)

        if args.stop:
            self.audience_stop(args)

        if args.add:
            sel = args.audience
            for section in self.challenges.keys():
                if sel in '*' or sel in section :
                    self.audience_add(section, args)

        if args.list:
            for section in self.challenges.keys():
                if section not in 'last_challenge' and self.challenges[section].as_bool('audience'):
                    print (section, ' audience ', self.challenges[section].as_bool('audience') , ' votes', \
                    self.challenges[section]['challenge_votes'], 'players', self.challenges[section][
                        'challenge_players'])

    def ranking(self, args):
        challenges = self.get_joined_challenges()
        if args.start:
            self.ranking_start(args)

        if args.stop:
            self.ranking_stop(args)

        if args.add:
            for challenge in challenges["challenges"]:
                if args.challenge in challenge["url"]:
                    self.ranking_add(challenge, args)

        if args.list:
            for section in self.challenges.keys():
                if section not in 'last_challenge' and self.challenges[section].as_bool('ranking'):
                    print (section, ' ranking ',self.challenges[section].as_bool('ranking') , ' votes', \
                    self.challenges[section]['challenge_votes'], 'players', self.challenges[section][
                        'challenge_players'])

    def ranking_add(self, challenge, args):
        print ('ranking ' + challenge['title'])
        self.challenges[challenge['url']]['ranking'] = True
        #self.challenges[challenge['url']]['ranking_delay'] = args.delay
        self.challenges.write()

    def ranking_start(self, args):
        self.rankingThread = threading.Thread(target=self.audience_thread, name='audience')
        self.rankingThread.daemon = True  # Daemonize thread
        self.rankingThread.start()
        self.config['process']['ranking'] = self.rankingThread.name
        self.config.write()


    def ranking_stop(self, args):
        self.stillRankingRunning = False
        self.rankingThread.join()
        self.config['process']['ranking'] = ''
        self.config.write()


    def fill(self, args):
        if args.player:
            player = args.player
            args.set = True
            self.players(args)

        if args.cha:
            sel = args.cha
        else:
            sel = self.config['players'][self.player]['last_challenge']

        for section in self.challenges.keys():
            if sel in '*' or sel in section :
                self.action_exec_args(section, "fill", args.fill,  args)
                self.config['challenge'] = section
                self.config.write()

    def vote(self, args):
        if args.player:
            player = args.player
            args.set = True
            self.players(args)

        if args.cha:
            sel = args.cha
        else:
            sel = self.config['players'][self.player]['last_challenge']

        for section in self.challenges.keys():
            if sel in '*' or sel in section :
                self.action_exec_args(section, "vote", args.vote, args)
                self.config['challenge'] = section
                self.config.write()

    def swap(self, args):
        if args.cha:
            sel = args.cha
        else:
            sel = self.config['players'][self.player]['last_challenge']

        for section in self.challenges.keys():
            if sel in '*' or sel in section :
                #print(self.challenges[section]['member']['ranking']['entries'][int(args.swap)-1]['id'])
                #self.action_exec_args(section, "swap", self.challenges[section]['member']['ranking']['entries'][int(args.swap)-1]['id'], args)
                self.action_exec_args(section, "swap", args.swap, args)
                self.config['challenge'] = section
                self.config.write()

    def unlock(self, args):
        if args.unlock:
            sel = args.unlock
        else:
            sel = self.config['players'][self.player]['last_challenge']

        for section in self.challenges.keys():
            if sel in '*' or sel in section :
                self.action_exec_args(section, "unlock", section, args)
                self.config['challenge'] = section
                self.config.write()

    def boost(self, args):
        if args.cha:
            sel = args.cha
        else:
            sel = self.config['players'][self.player]['last_challenge']

        for section in self.challenges.keys():
            if  sel in section :
                self.action_exec_args(section, "boost", args.boost, args)
                self.config['challenge'] = section
                self.config.write()


    def submit(self, args):
        if args.cha:
            sel = args.cha
        else:
            sel = self.config['players'][self.player]['last_challenge']

        for section in self.challenges.keys():
            if sel in '*' or sel in section :
                self.action_exec_args(section, "submit", args.submit, args)
                self.config['challenge'] = section
                self.config.write()


    def log(self, args):
        if args.log in '.':
            sel = self.config['players'][self.player]['last_challenge']

        for section in self.challenges.keys():
            if sel in '*' or sel in section :
                self.action_exec_args(section, "log", section, '', args)
                self.config['challenge'] = section
                self.config.write()


    def ps(self, args):
        if args.pop:
            self.ps_pop(args.pop)

        if args.purge:
            self.ps_purge(args)

        if args.restart:
            self.ps_restart(args)

        if args.restart:
            self.ps_stop(args)

        if args.list:
            self.ps_list()

    def ps_pop(self, p_id):
        for process_id in self.config['players'][self.player]['process'].keys():
            if p_id in process_id:
                self.config['players'][self.player]['process'].pop(process_id)
                if self.config['players'][self.player].get('cmdes') is not None and self.config['players'][self.player]['cmdes'].get(process_id) is not None:
                    self.config['players'][self.player]['cmdes'].pop(process_id)
                self.config.write()
                print ("process : ", process_id, "killed")

    def ps_update(self, process_id, status):
        self.config['players'][self.player]['process'][process_id] = status
        self.config.write()
        print ("process : ", process_id, status)

    def ps_list(self):
        for process_id in self.config['players'][self.player]['process'].keys():
            print ("process id  : ", process_id, "process name", self.config['players'][self.player]['process'][process_id])

    def ps_restart(self, args):
        for process_id in self.config['players'][self.player]['process'].keys():
            if self.config['players'][self.player]['process'][process_id] in 'waiting':
                args = self.parser.parse_args(self.config['players'][self.player]['cmdes'][process_id].split())
                args.func(args)
            else:
                self.ps_pop(process_id)

    def ps_stop(self, args):
        for process_id in self.config['players'][self.player]['process'].keys():
            if args.ps in process_id and self.config['players'][self.player]['process'][process_id] in 'waiting':
                self.ps_update(process_id, 'stop'):

    def ps_purge(self, args):
        for process_id in self.config['players'][self.player]['process'].keys():
            self.ps_pop(process_id)


    def ps_add(self, process_id,  status, action, value, args):
        if self.config['players'][self.player].get('process') == None:
            self.config['players'][self.player]['process']= {}

        self.config['players'][self.player]['process'][process_id] = status
        self.config.write()
        self.cmde_add(process_id, action, value, args)
        print ('process', process_id, status)

    def cmde_list(self, process_id, status, args):
        for process_id in self.config['players'][self.player]['cmdes'].keys():
            print (self.config['players'][self.player]['cmdes'][process_id])

    def cmde_add(self, process_id, action, value, args):
        if self.config['players'][self.player].get('cmdes') == None:
            self.config['players'][self.player]['cmdes']= {}
        if self.config['players'][self.player]['cmdes'].get(process_id) == None:
            self.config['players'][self.player]['cmdes'][process_id] = args.cmde
            self.config.write()
            #print 'cmde', args.cmde
        else:
            print ('cmde', args.cmde , 'already exist')

    def players(self, args):
        if args.set:
            self.player = args.player
            self.config['player'] = args.player
            self.config.write()
            self.xtoken = self.config['players'][args.player]['xtoken']
            self.connect()

        if args.list:
            for player in self.config['players'].keys():
                print ("player : ", player)

    def strategie(self, args):
        if args.start:
            sel = self.challenge
            if args.cha:
                for section in self.challenges.keys():
                    if args.cha in section:
                        sel = section
            for _strategie in self.strategies.keys():
                if args.strategie in _strategie:
                    for step in self.strategies[_strategie].keys():
                        cmd = self.strategies[_strategie][step]+' --cha ' + str(sel)
                        cmd_args = self.parser.parse_args(cmd.split())
                        cmd_args.cmde = cmd
                        cmd_args.func(cmd_args)

        if args.list:
            for strategie in self.strategies.keys():
                print ("strategie : ", strategie)
                for step in self.strategies[strategie].keys():
                    print ("step : ", step, self.strategies[strategie][step])
        else:
            print (args.strategie)

    def member(self, args):
        sel = args.member
        self.member_id = str(self.get_member_id())
        if args.stop:
            if args.cha:
                for section in self.challenges.keys():
                    if args.cha in section:
                        followings = self.get_followings(self.member_id, args)
                        for following in followings["items"]:
                            if sel in '*' or sel in following['member']["user_name"]:
                                args.member = following['member']["user_name"]
                                if args.vote:
                                    self.members[following["member"]["id"]]['stop'] = True
                                    args.vote = False
                                if args.watch:
                                    self.followings[following["member"]["id"]]['stop'] = True
                                    args.watch = False
        if args.vote and args.photo is not '':
            for section in self.challenges.keys():
                if args.cha in section:
                    followings = self.get_followings(self.member_id, args)
                    for following in followings["items"]:
                        if sel in '*' or sel in following['member']["user_name"]:
                            args.member = following['member']["user_name"]
                            self.members[str(following["member"]["id"])] = {}
                            self.members[str(following["member"]["id"])]['stop'] = False
                            self.action_exec_args(section, "photo", following["member"]["id"], args)

        if args.vote and args.photo is '':
            for section in self.challenges.keys():
                if args.cha in section:
                    followings = self.get_followings(self.member_id, args)
                    for following in followings["items"]:
                        if sel in '*' or sel in following['member']["user_name"]:
                            args.member = following['member']["user_name"]
                            self.members[str(following["member"]["id"])] = {}
                            self.members[str(following["member"]["id"])]['stop'] = False
                            self.action_exec_args(section, "member", following["member"]["id"], args)

        if args.watch:
            for section in self.challenges.keys():
                if args.cha in section:
                    followings = self.get_followings(self.member_id, args)
                    for following in followings["items"]:
                        if sel in '*' or sel in following['member']["user_name"]:
                            args.member = following['member']["user_name"]
                            self.watchings[str(following["member"]["id"])] = {}
                            self.watchings[str(following["member"]["id"])]['stop'] = False
                            self.action_exec_args(section, "watch", following["member"]["id"], args)


        if args.list:
            followings = self.get_followings(self.member_id, args)
            for following in followings["items"]:
                if sel in '*' or sel in following['member']["user_name"]:
                     print (following["member"]["user_name"])

    def challenge_batch(self, section, key, encode=False):
        print('Challenge ' + key)
        self.batchChallenge(key)

    def get_challenge(self, challenge):
        # Attempt to login to Facebook
        response = self.aio_post('https://gurushots.com/rest/get_page_data', data={
            'url': 'https://gurushots.com/challenge/' + challenge + '/details'
        })
        return json.loads(response)

    def get_member(self, challenge):
        # Attempt to login to Facebook
        response = self.aio.post('https://gurushots.com/rest/get_page_data', data={
            'url': 'https://gurushots.com/challenge/' + challenge + '/details'
        })

        return json.loads(response)

    def connect(self):
        # challenge = 4257

        self.session = requests.session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '4',
            'x-env': 'WEB',
            'X-requested-with': 'XMLHttpRequest',
            'X-token': self.xtoken
        })

    def player_connect(self, args):
        # challenge = 4257

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '4',
            'x-env': 'WEB',
            'X-requested-with': 'XMLHttpRequest',
            'X-token': self.config['players'][args.player]['xtoken']
        })
        return session

    def submit_to_challenge(self, challenge_id, photo_id):
        if self.session:
            images=[]
            images.append(photo_id)
            payload = {'image_ids['+str(id)+']': value for id, value in enumerate(images)}
            payload['c_id'] = challenge_id
            payload['el'] = 'my_challenge_current'
            payload['el_id'] = True
            response = self.aio.post('https://gurushots.com/rest/submit_to_challenge', data=payload)
            return json.loads(response)
        return {}

    def boost_photo(self, challenge_id, photo_id):
        if self.session:
            images=[]
            images.append(photo_id)
            payload = {'image_id': photo_id}
            payload['c_id'] = challenge_id
            response = self.aio_post('https://gurushots.com/rest/boost_photo', data=payload)
            return json.loads(response)
        return {}

    def swap_photo(self, challenge_id, photo_id, new_photo_id):
        if self.session:
            payload={'c_id': challenge_id}
            payload['el'] = 'my_challenge_current'
            payload['el_id'] = True
            payload['img_id'] = photo_id.encode()
            payload['new_img_id'] = new_photo_id.encode()
            response = self.aio_post('https://gurushots.com/rest/swap', data=payload)
            return json.loads(response)
        return {}

    def unlock_key(self, challenge_id, boost):
        if self.session:
            payload={'c_id' : challenge_id}
            if boost:
                payload['usage'] = 'EXPOSURE_BOOST'
            else:
                payload['usage'] = 'JOIN_CHALLENGE'
            response = self.aio_post('https://gurushots.com/rest/key_unlock', data=payload)
            return json.loads(response)
        return {}

    def get_followings(self, id, args):
        # get vote_ data
        response_panel = self.aio_post('https://gurushots.com/rest/get_following', data={
            'id': id,
            'limit': args.limit,
            'start': args.start
        })
        return json.loads(response)

    def get_member_id(self):
        # get vote_ data
        response_panel = self.aio_post('https://gurushots.com/rest/get_page_data', data={
            'url': 'https://gurushots.com/challenges/my-challenges/current'

        return json.loads(response_panel)['items']['page']['member_path']['id']


    def get_following_photos(self, id, args):
        response_panel = self.aio_post('https://gurushots.com/rest/get_top_photos', data={
            'id': id,
            'filter': 'following',
            'limit': 200,
            'start': 0
        })
        return json.loads(content_panel)

    def run(self):
        print ('Action')

    def shell(self, args):
        print('shell...')

    def bye(self, args):
        print('bye...')
        self.bye = True
    def prompt(self, args):
        print('Hello!')


def interactive_shell():
    """
    Like `interactive_shell`, but doing things manual.
    """
    batch = GuruBatch()
    args = batch.parser.parse_args()
    batch.init(args)


    our_history = FileHistory('.example-history-file')

    # Create Prompt.
    session = PromptSession('Say something: ', history=our_history)

    # Run echo loop. Read text from stdin, and reply it back.
    while True:
        try:
            result = session.prompt('>>', default='')
            print('You said: "{0}"'.format(result))
            if result is not '':
                if 'bye' in result:
                    return
                else:
                    args = batch.parser.parse_args(result.split())
                    args.func(args)
        except (EOFError, KeyboardInterrupt):
            return

def main():
    with patch_stdout():
         interactive_shell()
         print('Quitting event loop. Bye.')


if __name__ == '__main__':
    main()


