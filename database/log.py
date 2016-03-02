import time


def log(exc: str, func_name: str):
    with open('database/log.txt', 'a') as outp:
        outp.write('T:{}FUNC:{}\nMSG:{}\n'.format(time.time(), func_name, exc))
