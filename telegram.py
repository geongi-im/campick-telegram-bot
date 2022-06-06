import pymysql
import pymysql.cursors
import telegram
import datetime
import time
import json
from telegram.ext import Updater
from telegram.ext import MessageHandler, Filters

telegramToken = 'token' #챗봇Token

bot = telegram.Bot(token = telegramToken)
updater = Updater(token=telegramToken, use_context=True)
dispatcher = updater.dispatcher
updater.start_polling()

def sendMessage(text, chatId) :
    bot.sendMessage(chat_id = chatId, text = text, parse_mode='HTML')

def getConnection():
    conn = pymysql.connect(host='dbhost', user='dbuser', password='dbpassword', db='dbname', charset='utf8')
    return conn

def getMonitorList(userId, chatId) :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT A.m_continue_day as day, A.m_place_code as code, B.pl_name as name, A.m_reserve_date as date FROM cp_monitor as A INNER JOIN cp_place_list as B ON A.m_place_code = B.pl_code WHERE A.m_user_id = '" + userId + "' AND A.m_chat_id = '" + chatId + "'"
    cursor.execute(sql)
    rows = cursor.fetchall()

    if len(rows) == 0 :
        return '[안내] 등록된 내역이 없습니다'
        
    message = '[모니터링 리스트]\n'
    for row in rows :
        message += '캠핑장 : ' + row['name'] + '(' + row['code'] + ')\n예약일 : ' + row['date'] + '\n일수 : ' + str(row['day']) + '\n\n'
    
    conn.close()
    return message

def getPlaceList() :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = 'SELECT * FROM cp_place_list'
    cursor.execute(sql)
    rows = cursor.fetchall()
    message = '[캠핑장 리스트]\n'
    for row in rows :
        message += '<b>' + row['pl_name'] + '</b>\n'
        message += '캠핑장코드 : ' + row['pl_code'] + '\n'
        message += '전화번호 : ' + row['pl_tel'] + '\n'
        message += '홈페이지 : <a href="' + row['pl_url'] + '">바로가기</a>\n'
        if row['pl_open_yn'] == 1 :
            message += '알림상태 : \U0001F7E2 OPEN\n\n'
        else :
            message += '알림상태 : \U0001F534 CLOSE\n\n'
    
    conn.close()
    return message

def getHelp() :
    message = '[도움말] 명령어를 메시지로 보내시면 됩니다.\n\n'
    message += '* 모니터링 할수있는 캠핑장들을 조회하는 명령어\n<b>\U0001F4CB /리스트</b>\n\n'
    message += '* 모니터링 할 캠핑장 등록하는 명령어\n<b>\U00002705 /등록 캠핑장코드 날짜(yymmdd)</b>\n캠핑장 코드는 리스트에 등록된 코드여야합니다(대소문자 구분X)\nex) /등록 SR 210924\nex) /등록 hm 211011\nex) /등록 CMD 220124\n\n'
    message += '* 장박할 캠핑장 등록하는 명령어\n<b>\U00002705 /장박 캠핑장코드 날짜(yymmdd) 일수(n)</b>\n현재 장박기능은 화명/대저/부산항캠핑장/황산(오토)만 가능합니다.\nex) /장박 DJ 210924 2\nex) /장박 hm 211011 2\nex) /장박 BH 220124 2\n\n'
    message += '* 모니터링에 등록된 캠핑장 삭제하는 명령어\n<b>\U0000274C /삭제 캠핑장코드 날짜(yymmdd)</b>\nex) /삭제 SR 210924\nex) /삭제 hm 211011\nex) /삭제 CMD 220124\n\n'
    message += '* 장박에 등록된 캠핑장 삭제하는 명령어\n<b>\U0000274C /장삭 캠핑장코드 날짜(yymmdd) 일수(n)</b>\nex) /장삭 SR 210924 2\nex) /장삭 hm 211011 2\nex) /장삭 CMD 220124 2\n\n'
    message += '* 모니터링에 등록된 캠핑장을 조회하는 명령어\n<b>\U0001F50E /조회</b>\n\n'
    message += '* 캠핑장 모니터링에 제안 혹은 수정 사항을 등록하는 명령어\n<b>\U0001F44D /제안 내용</b>\nex) /제안 OO캠핑장 추가\nex) /제안 OO기능도 추가해주세요'
    return message

def changeFormatDate(date) :
    if len(date) == 6 :
        date = '20' + date[:2] + '-' + date[2:4] + '-' + date[4:6]
    elif len(date) == 8 :
        date = date[:4] + '-' + date[4:6] + '-' + date[6:8]
    return date

def isValidCode(code) :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT pl_name FROM cp_place_list WHERE pl_code = '" + code + "'"
    cursor.execute(sql)
    row = cursor.fetchone()
    conn.close()

    if row != None :
        return True
    else :
        return False

def isDuplicateCode(userId, chatId, code, date, day='1') :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "SELECT m_date FROM cp_monitor WHERE m_user_id = '" + userId + "' AND m_chat_id = '" + chatId + "' AND m_place_code = '" + code + "' AND m_continue_day = '" + day + "' AND m_reserve_date = '" + date + "'"
    cursor.execute(sql)
    row = cursor.fetchone()
    conn.close()

    if row != None :
        return True
    else :
        return False

def isValidDate(date) :
    if len(date) != 6 and len(date) != 8 :
        return False
    try :
        if len(date) == 6 :
            datetime.datetime.strptime(date, '%y%m%d')
        elif len(date) == 8 :
            datetime.datetime.strptime(date, '%Y%m%d')
    except ValueError:
        return False
    else :
        return True

def insertProposal(userId, chatId, content) :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "INSERT INTO cp_user_proposal SET\
            up_user_id = '" + userId + "',\
            up_content = '" + content + "',\
            up_date = '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'\
        "
    cursor.execute(sql)
    conn.commit()
    conn.close()

def insertLog(userId, chatId, content) :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "INSERT INTO cp_log SET\
            lg_user_id = '" + userId + "',\
            lg_chat_id = '" + chatId + "',\
            lg_content = '" + content + "',\
            lg_date = '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'\
        "
    cursor.execute(sql)
    conn.commit()
    conn.close()

def insertUser(userInfo) :
    userId = str(userInfo.id)
    userFullName = userInfo.full_name
    userName = userInfo.username

    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "INSERT INTO cp_user_info SET\
            ui_id = '" + userId + "',\
            ui_name = '" + userName + "',\
            ui_full_name = '" + userFullName + "',\
            ui_date = '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'\
        "
    cursor.execute(sql)
    conn.commit()
    conn.close()

def insertMonitorPlace(userId, chatId, code, date, day='1') :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "INSERT INTO cp_monitor SET\
            m_user_id = '" + userId + "',\
            m_chat_id = '" + chatId + "',\
            m_place_code = '" + code + "',\
            m_reserve_date = '" + date + "',\
            m_continue_day = '" + day + "',\
            m_date = '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'\
        "
    cursor.execute(sql)
    conn.commit()
    conn.close()

def deleteMonitorPlace(userId, chatId, code, date, day) :
    conn = getConnection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = "DELETE FROM cp_monitor WHERE m_user_id = '" + userId + "' AND m_chat_id = '" + chatId + "' AND m_place_code = '" + code + "' AND m_continue_day = '" + str(day) + "' AND  m_reserve_date = '" + date + "'";
    result = cursor.execute(sql)
    conn.commit()
    conn.close()
    return result

def handler(update, context) :
    responseText = update.message.text
    chatId = str(update.message.chat_id)
    userId = str(update.message.from_user.id)

    insertLog(userId, chatId, responseText)

    if responseText == '/도움말' or responseText == '/도움' or responseText == '/help' or responseText == '/h' or responseText == '/메뉴얼' :
        helpMessage = getHelp()
        sendMessage(helpMessage, chatId)
    elif responseText == '/조회' :
        monitorMessage = getMonitorList(userId, chatId)
        sendMessage(monitorMessage, chatId)
    elif responseText == '/start' :
        sendMessage('안녕하세요\n자세한 사용법은 /도움말 을 입력해주세요', chatId)
        insertUser(update.message.from_user)
    elif responseText == '/리스트' or responseText == '/list' :
        placeMessage = getPlaceList()
        sendMessage(placeMessage, chatId)
    elif responseText.startswith('/제안') :
        text = responseText.split()
        if len(text) != 2 :
            sendMessage('[에러] 명령어를 올바르게 입력해주세요\n\n/제안 내용\nex) /제안 OO캠핑장 추가\nex) /제안 OO기능도 추가해주세요', chatId)
        else :
            content = text[1]
            insertProposal(userId, chatId, content)
            sendMessage('[안내] 감사합니다. 보내주신 제안은 검토 후 빠른 시일내에 반영하겠습니다.', chatId)
    elif responseText.startswith('/삭제') :
        text = responseText.split()
        if len(text) != 3 :
            sendMessage('[에러] 명령어를 올바르게 입력해주세요\n\n/삭제 캠핑장코드 날짜(yymmdd)\n캠핑장 코드는 리스트에 등록된 코드여야합니다(대소문자 구분X)\nex) /삭제 SR 210924\nex) /삭제 hm 211011\nex) /삭제 CMD 220124', chatId)
        else :
            code = text[1].upper()
            date = text[2].replace('-', '')

            if isValidCode(code) != True :
                sendMessage('[에러] 모니터링 삭제를 실패하였습니다\n캠핑장 코드를 다시 확인해주세요.', chatId)
            elif isValidDate(date) != True :
                sendMessage('[에러] 모니터링 삭제를 실패하였습니다\n날짜(yymmdd)를 올바르게 입력해주세요.', chatId)
            else :
                if deleteMonitorPlace(userId, chatId, code, changeFormatDate(date), 1) > 0 :
                    sendMessage('[안내] 모니터링이 정상적으로 삭제되었습니다', chatId)
                else :
                    sendMessage('[에러] 모니터링 삭제를 실패하였습니다\n다시 확인해주세요.', chatId)
    elif responseText.startswith('/장삭') :
        text = responseText.split()
        if len(text) != 4 :
            sendMessage('[에러] 명령어를 올바르게 입력해주세요\n\n/장삭 캠핑장코드 날짜(yymmdd) 일수(n)\n캠핑장 코드는 리스트에 등록된 코드여야합니다(대소문자 구분X)\nex) /장삭 DJ 210924 2\nex) /장삭 hm 211011 2\nex) /장삭 BH 220124 2', chatId)
        else :
            code = text[1].upper()
            date = text[2].replace('-', '')
            day = text[3]

            if isValidCode(code) != True :
                sendMessage('[에러] 모니터링 삭제를 실패하였습니다\n캠핑장 코드를 다시 확인해주세요.', chatId)
            elif isValidDate(date) != True :
                sendMessage('[에러] 모니터링 삭제를 실패하였습니다\n날짜(yymmdd)를 올바르게 입력해주세요.', chatId)
            else :
                if deleteMonitorPlace(userId, chatId, code, changeFormatDate(date), day) > 0 :
                    sendMessage('[안내] 모니터링이 정상적으로 삭제되었습니다', chatId)
                else :
                    sendMessage('[에러] 모니터링 삭제를 실패하였습니다\n다시 확인해주세요.', chatId)
    elif responseText.startswith('/장박') :
        text = responseText.split()
        if len(text) != 4 :
            sendMessage('[에러] 명령어를 올바르게 입력해주세요\n\n/장박 캠핑장코드 날짜(yymmdd) 일수(n)\n캠핑장 코드는 리스트에 등록된 코드여야합니다(대소문자 구분X)\nex) /장박 HM 210924 2\nex) /장박 hm 211011 2\nex) /장박 BH 220124 2', chatId)
        else :
            code = text[1].upper()
            date = text[2].replace('-', '')
            day = text[3]

            if code != 'DJ' and code != 'HM' and code != 'BH' and code != 'HSA' :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n현재 장박기능은 화명/대저/부산항캠핑장/황산(오토)만 가능합니다.', chatId)
            elif int(day) > 2 :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n최대 장박일수는 2박입니다.', chatId)
            elif isValidCode(code) != True :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n캠핑장 코드를 다시 확인해주세요.', chatId)
            elif isValidDate(date) != True :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n날짜(yymmdd)를 올바르게 입력해주세요.', chatId)
            elif isDuplicateCode(userId, chatId, code, changeFormatDate(date), day) :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n중복 등록은 할 수 없습니다.', chatId)
            else :            
                insertMonitorPlace(userId, chatId, code, changeFormatDate(date), day)
                sendMessage('[안내] 모니터링이 정상적으로 등록되었습니다', chatId)
    elif responseText.startswith('/등록') :
        text = responseText.split()
        if len(text) != 3 :
            sendMessage('[에러] 명령어를 올바르게 입력해주세요\n\n/등록 캠핑장코드 날짜(yymmdd)\n캠핑장 코드는 리스트에 등록된 코드여야합니다(대소문자 구분X)\nex) /등록 SR 210924\nex) /등록 hm 211011\nex) /등록 CMD 220124', chatId)
        else :
            code = text[1].upper()
            date = text[2].replace('-', '')

            if isValidCode(code) != True :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n캠핑장 코드를 다시 확인해주세요.', chatId)
            elif isValidDate(date) != True :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n날짜(yymmdd)를 올바르게 입력해주세요.', chatId)
            elif isDuplicateCode(userId, chatId, code, changeFormatDate(date)) :
                sendMessage('[에러] 모니터링 등록이 실패하였습니다\n중복 등록은 할 수 없습니다.', chatId)
            else :            
                insertMonitorPlace(userId, chatId, code, changeFormatDate(date))
                sendMessage('[안내] 모니터링이 정상적으로 등록되었습니다', chatId)
    else :
        sendMessage('[에러] 등록되지 않은 명령어입니다\n/도움말 을 확인해주세요', chatId)

echo_handler = MessageHandler(Filters.text, handler)
dispatcher.add_handler(echo_handler)
