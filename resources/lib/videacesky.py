# -*- coding: UTF-8 -*-
# /*
# *      Copyright (C) 2013 Libor Zoubek
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */

import sys

import re
import urllib
import http.cookiejar
from demjson import demjson

import util
from contentprovider.provider import ResolveException
from contentprovider.provider import ContentProvider

class VideaceskyContentProvider(ContentProvider):
    def __init__(self, username=None, password=None, filter=None, original_yt=False,
                 tmp_dir='/tmp'):
        ContentProvider.__init__(self, 'videacesky.cz',
                                 'http://www.videacesky.cz',
                                 username, password, filter, tmp_dir)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.LWPCookieJar()))
        urllib.request.install_opener(opener)
        self.original_yt = original_yt

    def capabilities(self):
        return ['categories', 'resolve', 'search']

    def list(self, url):
        if url.find('zebricky/') == 0:
            return self.list_top10(util.request(self.base_url+url))
        if url.find("#related#") == 0:
            return self.list_related(util.request(url[9:]))
        if url.find("#show#") == 0:
            return self.list_content(util.request(url[6:]))    
        else:
            return self.list_content(util.request(self._url(url)), self._url(url))

    def search(self, keyword):
        return self.list('/hledat?q=' + urllib.parse.quote(keyword))

    def mmss_to_seconds(self, mmss):
        minutes, seconds = [int(x) for x in mmss.split(':')]
        return (minutes * 60 + seconds)

    def categories(self):
        result = []
        item = self.dir_item()
        item['type'] = 'new'
        item['url'] = "?orderby=post_date"
        result.append(item)
        item = self.dir_item()
        item['title'] = 'Top of the month'
        item['url'] = "zebricky/mesic/vse"
        result.append(item)
        data = util.request(self.base_url)
        data = util.substr(data, '<ul class=\"nav categories m-b\">', '</div>')
        pattern = '<a href=\"(?P<url>[^\"]+)(.+?)>(?P<name>[^<]+)'
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            if m.group('url') == '/':
                continue
            item = self.dir_item()
            item['title'] = m.group('name')
            item['url'] = m.group('url')
            result.append(item)
        return result

    def list_top10(self, page):
        result = []
        data = util.substr(page,
                           '<div class=\"line-items no-wrapper no-padder',
                           '<div class=\"my-pagination>')
        pattern = '<article class=\"video-line.+?<a href=\"(?P<url>[^\"]+)\" *title=\"(?P<title>[^\"]+)\".+?<img src=\"(?P<img>[^\"]+)\".+?<div class=\"video-rating.+?\">(?P<rating>[^&]+).+?<small>(?P<votes>[^x]+)'
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['title'] = self.format_title(m)
            item['url'] = self.base_url[:-1] + m.group('url')
            item['img'] = m.group('img').strip()
            item['plot'] = self.format_rating(m)
            self._filter(result, item)
        return result

    def list_content(self, page, url=None):
        result = []
        if not url:
            url = self.base_url
        data = util.substr(page, '<div class=\"items no-wrapper no-padder', '<div class=\"my-pagination>')
        pattern = '<article class=\"video[ ]?(?P<collection>[^\"]*)\" id=.+?<a href=\"(?P<url>[^\"]+)\" *title=\"(?P<title>[^\"]+)\".+?<img src=\"(?P<img>[^\"]+)\".+?<span class=\"duration\">(?P<duration>[^>]*)</span>.*?<span class="rating[^"]+">(?P<rating>[^&]+).+?<a href=\"(?P<show_url>[^\"]+)\" title=.+?<p>(?P<plot>[^<]+?)<\/p>.+?<li class=\"i-published\".+?title=\"(?P<date>[^\"]+)\".+?<i class=\"fa fa-eye\"></i><span class=\"value\">(?P<votes>[^<]+)'
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['title'] = self.format_title(m)
            item['img'] = m.group('img').strip()
            item['plot'] = self.decode_plot(m)
            item['year'] = re.search('[0-9]{4}', m.group('date')).group()
            item['url'] = self.base_url[:-1] + m.group('url')
            item['menu'] = {
                '$30060': {'list': '#related#' + item['url'],'action-type': 'list'},
                '$30062': {'list': '#show#' + self.base_url + m.group('show_url')[1:],'action-type': 'list'}
            }
            try:
                item['duration'] = self.mmss_to_seconds(m.group('duration'))
            except ValueError:
                pass
            self._filter(result, item)
        data = util.substr(page, '<ul class=\"my-pagination', '</div>')
        n = re.search('<li class=\"paginate_button previous *\"[^<]+<a href=\"(?P<url>[^\"]+)\">(?P<name>[^<]+)<', data)
        k = re.search('<li class=\"paginate_button next *\"[^<]+<a href=\"(?P<url>[^\"]+)\">(?P<name>[^<]+)<', data)
        if n is not None:
            item = self.dir_item()
            item['type'] = 'prev'
            # item['title'] = '%s - %s' % (m.group(1), n.group('name'))
            item['url'] = n.group('url')
            result.append(item)
        if k is not None:
            item = self.dir_item()
            item['type'] = 'next'
            # item['title'] = '%s - %s' % (m.group(1), k.group('name'))
            item['url'] = k.group('url')
            result.append(item)
        print ('==list_content==')
        print ('result')
        return result

    def list_related(self, page):
        result = []
        data = util.substr(page,
                           '<div class=\"similarSliderInner\"',
                           '<div class=\"comments-container\"')
        pattern = '<article class=\"videoSimple.+?<a href=\"(?P<url>[^\"]+)\" *title=\"(?P<title>[^\"]+)\".+?<img src=\"(?P<img>[^\"]+)\".+?<span class="rating.+?>(?P<rating>[^&]+)'
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['title'] = self.format_title(m)
            item['img'] = m.group('img')
            item['url'] = m.group('url')
            self._filter(result, item)
        return result

    def format_title(self, m):
        collection = m.group('collection')
        if collection is not None and len(collection) > 0:
            return "{0} - {1}%, {2}".format(m.group('title'), m.group('rating'), collection)
        else:
            return "{0} - {1}%".format(m.group('title'), m.group('rating'))

    def format_rating(self, m):
        return "{0}%, {1}x".format(m.group('rating'), m.group('votes'))

    def decode_plot(self, m):        
        p = m.group('plot')
        p = re.sub('<br[^>]*>', '', p)
        p = re.sub('<div[^>]+>', '', p)
        p = re.sub('<table.*', '', p)
        p = re.sub('</span>|<br[^>]*>|<ul>|</ul>|<hr[^>]*>', '', p)
        p = re.sub('<span[^>]*>|<p[^>]*>|<li[^>]*>', '', p)
        p = re.sub('<strong>|<a[^>]*>|<h[\d]+>', '[B]', p)
        p = re.sub('</strong>|</a>|</h[\d]+>', '[/B]', p)
        p = re.sub('</p>|</li>', '[CR]', p)
        p = re.sub('<em>', '[I]', p)
        p = re.sub('</em>', '[/I]', p)
        p = re.sub('<img[^>]+>', '', p)
        p = re.sub('\[B\]Edituj popis\[\/B\]', '', p)
        p = re.sub('\[B\]\[B\]', '[B]', p)
        p = re.sub('\[/B\]\[/B\]', '[/B]', p)
        p = re.sub('\[B\][ ]*\[/B\]', '', p)
        plot = util.decode_html(''.join(p)).strip()
        #plot = util.decode_html(''.join(p)).encode('utf-8').strip()
        rating = self.format_rating(m)
        return "{0}\n{1}".format(rating, plot)

    def resolve(self, item, captcha_cb=None, select_cb=None):
        original_yt = self.original_yt
        self.info('original_yt  ' + str(original_yt) + ' ' + str(type(original_yt)))
        result = []
        resolved = []
        item = item.copy()
        url = self._url(item['url'])
        data = util.substr(util.request(url), 'async type', '</script>')
        # print ('data start ----')
        # print (data)
        # print ('data end ----')
        playlist = re.search('''new mfJWPlayer.+?(?P<jsondata>playlist:.+?)events:''',
                             data, re.MULTILINE | re.DOTALL)
        # print ('playlist start ----')
        # print (playlist)
        # print ('playlist end ----')
        jsondata = re.sub(' +',
                          ' ',
                          '{%s' % playlist.group('jsondata').replace('file:','"file":').replace('label:','"label":').replace('kind:','"kind":').replace('default:','"default":').replace('true','"true"').replace('],',']'))+'}'
        # print ('jsondata start ----')
        # print (jsondata)
        # print ('jsondata end ----')
        jsondata = demjson.decode(jsondata)

        for playlist_item in jsondata['playlist']:
            playlist_item['file'] = playlist_item['file'].replace('time_continue=1&', '')
            #self.info(playlist_item['file'])

            if original_yt:
                video_id = re.search(r"(youtu\.be/|watch\?v=)(.+)", playlist_item['file']).group(2)
                subs = playlist_item['tracks']
                
                item = self.video_item()
                try:
                    item['title'] = playlist_item['title']
                except KeyError:
                    pass

                item['url'] = "plugin://plugin.video.youtube/play/?video_id=" + video_id
                item['surl'] = playlist_item['image']
                item['subs'] = self.base_url[:-1]+subs[0]['file']
            
                result.append(item)
            else:
                import YDStreamExtractor

                vid = YDStreamExtractor.getVideoInfo(playlist_item['file'], quality=3) #quality is 0=SD, 1=720p, 2=1080p, 3=Highest Available

                if vid is None:
                    raise ResolveException('Zkus aktualizovat youtube-dl, nebo pouzij youtube addon')

                video_url = [vid.streams()[0]]
                # self.info(video_url)
                subs = playlist_item['tracks']
                if video_url and subs:
                    for i in video_url:
                        i['subs'] = self.base_url[:-1]+subs[0]['file']
                resolved += video_url[:]

                if not resolved:
                    raise ResolveException('Video nenalezeno')

                for i in resolved:
                    item = self.video_item()
                    try:
                        item['title'] = i['title']
                    except KeyError:
                        pass
                    item['url'] = i['xbmc_url']
                    item['quality'] = i['ytdl_format']['height']
                    item['surl'] = i['ytdl_format']['webpage_url']
                    item['subs'] = i['subs']
                    item['headers'] = {}
                    # self.info(item)
                    try:
                        item['fmt'] = i['fmt']
                    except KeyError:
                        pass
                    result.append(item)

        if len(result) > 0 and select_cb:
            # self.info(result)
            return select_cb(result)
       
        # print ('==resolve==')
        # print (result)
        return result

