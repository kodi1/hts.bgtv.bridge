#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import simplejson as json
import base64
import requests
from Crypto.Cipher import AES
import hashlib
import re

proxies = None
#proxies = {'http': "http://127.0.0.1:8182"}

json_url = 'http://live.bgtv.stream/bg.json'
headers = {
              'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0 Iceweasel/22.0'
            }

class data_live():
  def __init__(self, k, host, port):
    self.__data = {}
    self.__k = k
    self.__h = {}
    self.__mBaseUrl = None
    self.__ext_ip = None
    self.__host = host
    self.__port = port
    with open('chmap.json', 'r') as f:
      self.__chmap =json.load(f)
    self.__decode()

    retry = requests.packages.urllib3.util.Retry(
                                                  total=5,
                                                  read=5,
                                                  connect=5,
                                                  backoff_factor=1,
                                                  status_forcelist=[ 502, 503, 504 ],
                                                  )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)

    self.__s = requests.Session()
    self.__s.mount('http://', adapter)
    self.__s.mount('https://', adapter)

  def __runThis(self, decodedValue, encodedValue):
    #Key run = Utils.run(getApplicationContext(), this.runTemp);
    #Cipher c = Cipher.getInstance("AES/CBC/NoPadding");
    #c.init(2, run, new IvParameterSpec(decodedValue));
    aes = AES.new(self.__h['runTemp'].encode('utf-8'), AES.MODE_CBC, decodedValue)
    #return new String(Arrays.copyOfRange(c.doFinal(encodedValue), 0, 22), UrlUtils.UTF8);
    return aes.decrypt(encodedValue).decode('utf-8').strip('\0')

  def __GetHost(self, url_host):
    r = self.__s.get(
                      url_host,
                      headers=headers,
                      proxies=proxies
                    )

    if r.status_code != requests.codes.ok:
      sys.exit('error fetch data %s' % r.status_code)

    return r.json().get('host')

  def __GetIp(self):
    r = self.__s.get(
                      self.__data.get('ip_gateway'),
                      headers=headers,
                      proxies=proxies
                    )

    if r.status_code != requests.codes.ok:
      sys.exit('error fetch data %s' % r.status_code)

    return r.json().get('ip')

  def __createUrl(self, url, ip, _uri):
    tempByte = base64.b64decode(self.__data.get('key'))
    mDecryptedValue = self.__runThis(tempByte[:16], tempByte[16:])
    tempValue = mDecryptedValue + self.__data.get('expire_timestamp') + _uri + self.__ext_ip
    #print ('%s - %d' % (mDecryptedValue, len(mDecryptedValue)))
    tempValue = hashlib.md5(tempValue.encode('utf-8')).digest()
    #print (tempValue)
    tempValue = base64.urlsafe_b64encode(tempValue).decode('utf-8').replace('=', '')
    #print (tempValue)
    return '%s%s?%s=%s&%s=%s' % (
                                  self.__mBaseUrl,
                                  _uri,
                                  self.__data.get('hash_param'),
                                  tempValue,
                                  self.__data.get('expire_param'),
                                  self.__data.get('expire_timestamp')
                                  )

  def __mk_id(self, n):
    return re.sub('\s|-', '_', n.lower())

  def __decode(self):
    with open('data.dat', 'rb') as f:
      d = f.read()
      obj = AES.new(self.__k.encode('utf-8'), AES.MODE_CFB, d[-AES.block_size:])
      self.__h = json.loads(obj.decrypt(base64.urlsafe_b64decode(d[:-AES.block_size])))
      print('decoded data:\n%s' % json.dumps(self.__h, indent=2, sort_keys=True))

  def __get_json(self):
    r = self.__s.get(
                      json_url,
                      headers=headers,
                      proxies=proxies
                    )

    if r.status_code != requests.codes.ok:
      sys.exit('error fetch data %s' % r.status_code)
    self.__data = r.json()

    self.__mBaseUrl = self.__data.get('baseUrl')
    mBalanceGatewayUrl = self.__data.get('balance_gateway').get('url')
    self.__ext_ip = self.__GetIp()

    if not self.__mBaseUrl and mBalanceGatewayUrl:
      self.__mBaseUrl = self.__GetHost(mBalanceGatewayUrl)

    if not self.__mBaseUrl or not self.__ext_ip:
      sys.exit('error mBaseUrl')

  def mkchmap(self):
      map_tags = {
          'Документални': 'Научни',
          'Политематични': 'ЕФИРНИ',
          'Новинарски': 'ДРУГИ'
      }
      self.__get_json()
      for chanel in self.__data.get('channels'):
        _id = self.__mk_id(chanel.get('name'))
        self.__chmap.update({_id: {'name': '', 'logo': '', 'id': '', 'tag': '', 'uri': chanel.get('uri')}})

      with open('freebgtv.m3u8', 'r') as t:
        for l in t:
          m = re.match(r'#EXTINF.*tvg-id="(.*)".*tvg-name="(.*)".*tvg-logo="(.*)".*group-title="(.*)".*,(.*)', l)
          if m:
            for k in list(self.__chmap.keys()):
              if m.group(1).lower() == re.sub('_', '', k):
                print(m.group(1))
                self.__chmap[k]['name'] = m.group(5)
                self.__chmap[k]['id'] = m.group(1)
                self.__chmap[k]['tag'] = map_tags.get(m.group(4), m.group(4))
                self.__chmap[k]['logo'] = m.group(3)
                break

      s = json.dumps(self.__chmap, indent=2, sort_keys=True, ensure_ascii=False, encoding='utf-8')
      print(s)
      with open('chmap.json', 'wb') as f:
        f.write(s.encode('utf-8'))

  def get_bgtvch(self, _id):
    #self.__get_json()
    _ch = self.__chmap.get(_id)
    if not _ch:
      return None
    return self.__createUrl(self.__mBaseUrl, self.__ext_ip, _ch.get('uri'))

  def get_bgtvlist(self):
    self.__get_json()
    _line = '#EXTM3U\n'
    for k, v in list(self.__chmap.items()):
      extinf = 'tvh-epg="off"'

      logo = v.get('logo')
      if logo:
        extinf = '%s tvg-logo="%s"' % (extinf, logo)

      tvid = v.get('id')
      if tvid:
        extinf = '%s tvg-id="%s"' % (extinf, tvid)

      tag = v.get('tag')
      if tag:
        extinf = '%s tvh-tags="%s"' % (extinf, tag)

      name = v.get('name')
      if name:
        extinf = '%s,%s' % (extinf, name)
      else:
        extinf = '%s,%s' % (extinf, k)

      _line = _line + '#EXTINF:-1 %s\n' % (extinf,)
      #_line = _line + 'http://%s:%s/id/%s|User-Agent=%s\n' % (self.__host, self.__port, k, self.__h['ua'][0])
      _line = _line + 'pipe:///usr/bin/ffmpeg -loglevel fatal -ignore_unknown -headers "User-Agent: %s" -re -i http://%s:%s/id/%s -map 0 -c copy -metadata service_provider=bgtv -metadata service_name=%s -tune zerolatency -f mpegts pipe:1\n' % (self.__h['ua'][0], self.__host, self.__port, k, k)

    return _line

  def checkua(self, ua):
    for u in self.__h['ua']:
      if u in ua:
        return True
