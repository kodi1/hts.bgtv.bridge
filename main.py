#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os

def cmd_get_dbg():
  return input("q - quit\nr - restart\n")

def main():
    server.my_serv.start()
    try:
        while True:
            c = input("q - quit\nr - restart\n")
            if c:
              print(c)
            if c == "q":
                break;
            if c == "r":
                server.my_serv.restart()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt")
        pass

def __log(fmt, data):
    print(fmt % data)

if __name__ == "__main__":
    if 1 == len(sys.argv):
        import server
        server.log_cb = __log
        server.my_serv = server.serv(host=os.uname()[1])

        main()

        del server.my_serv
    else:
        import base64
        from Crypto import Random
        from Crypto.Cipher import AES

        b = Random.new().read(AES.block_size)
        obj = AES.new(sys.argv[1], AES.MODE_CFB, b)
        with open('./data.txt', 'rb') as fi:
            with open('./data.dat', 'wb') as f:
                f.write(base64.urlsafe_b64encode(obj.encrypt(fi.read())) + b)
