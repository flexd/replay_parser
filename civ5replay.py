#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# Read Civilization 5 Replay files 
# Written by Daniel Fischer (dannythefool), df.civ@erinye.com
#
# Contributions:
#   * Collin Grady:        Babylon colours, <html> header, replay files
#   * BotYann:             French translation, replay files
#   * player1 fanatic:     Usability suggestions
#   * blind biker:         Usability suggestions
#   * MouseyPounds:        DLC civs, further localization, patch 1.275 compatibility
# Forum names are on CivFanatics unless otherwise noted.
#
# Please note that this is based on reverse engineered serialiized data.
# If it doesn't work for you, please send me the replay file.
#
# This script can be used standalone or as a module.
#
# To run it standalone, just pass the path to a replay file as the only 
# argument on the command line, it'll output a lot of text that's really 
# inconvenient to read etc. etc.
#
# Run with -h to see available options (HTML export, etc.)
#

import os
import sys
import struct
import uuid
import optparse
import codecs
import signal
import re

# safety belt, comment in if you want a one minute timeout on a
# web server that runs Linux 
# signal.alarm(60)

# don't run in debug mode by default
debug = False

# cheap "I forgot about localization again even though English isn't even my native language" hack
locale = "auto"
class L(object):
    """ A localized string """
    def __init__(self, en, **kwargs):
        kwargs["en"] = en
        for k,v in kwargs.items():
           setattr(self, k, v.decode("utf-8"))
        self.s = self.__str__
        self.__repr__ = self.__str__
    def __str__(self):
        return self.__dict__.get(locale, self.en)
    def __mod__(self, x):
        return self.s() % x
    def __eq__(self, x):
        return self.s() == x
    def items(self):
        return self.__dict__.items()

def p(*s):
    """ Helper function replacing print for utf-8 output"""
    if debug:
      for e in s:
          if not isinstance(e, unicode):
              e = unicode(e)
          sys.stdout.write(e.encode("utf-8"))
          sys.stdout.write(" ")
      sys.stdout.write("\n")

# difficulty level names TXT_KEY_HANDICAP_* Still need ja and ru
difficulty_strings = [
    L("Settler",   fr="Colon",       de="Siedler",       es="Colono",    it="Colono",      ko="개척자", pl="Osadnik"),
    L("Chieftain", fr="Chef tribal", de="Häuptling",     es="Jefe",      it="Capitano",    ko="족장",  pl="Wódz"),
    L("Warlord",   fr="Seigneur",    de="Kriegsherr",    es="Caudillo",  it="Condottiero", ko="대장군", pl="Watażka"),
    L("Prince",    fr="Prince",      de="Prinz",         es="Príncipe",  it="Principe",    ko="왕자",  pl="Książę"),
    L("King",      fr="Roi",         de="König",         es="Rey",       it="Re",          ko="왕",   pl="Król"),
    L("Emperor",   fr="Empereur",    de="Kaiser",        es="Emperador", it="Imperatore",  ko="황제",  pl="Imperator"),
    L("Immortal",  fr="Immortel",    de="Unsterblicher", es="Inmortal",  it="Immortale",   ko="불멸자", pl="Nieśmiertelny"),
    L("Deity",     fr="Divinité",    de="Gottheit",      es="Deidad",    it="Divinità",    ko="신",   pl="Bóstwo"),

]

# map sizes TXT_KEY_WORLD_* Still need ja and ru
# this time, taken from the earth maps...
map_sizes = [
    [ L("Duel",     fr="Duel",      de="Duell",    es="Duelo",    it="Duello",    ko="일대일", pl="Pojedynkowa"), 40, 24 ],
    [ L("Tiny",     fr="Minuscule", de="Winzig",   es="Diminuto", it="Minuscola", ko="초소형", pl="Miniaturowa"), 56, 36 ],
    [ L("Small",    fr="Petite",    de="Klein",    es="Pequeño",  it="Piccola",   ko="소형",  pl="Mała"),        66, 42 ],
    [ L("Standard", fr="Normale",   de="Standard", es="Estándar", it="Normale",   ko="기본",  pl="Zwykła"),      80, 52 ],
    [ L("Large",    fr="Grande",    de="Groß",     es="Grande",   it="Grande",    ko="대형",  pl="Duża"),        104, 64 ],
    [ L("Huge",     fr="Immense",   de="Riesig",   es="Enorme",   it="Enorme",    ko="초대형", pl="Ogromna"),     128, 80 ],
]

# victory types TXT_KEY_CIV5_VICTORY_LOSS_TITLE and TXT_KEY_VICTORY_* Still need ja and ru
victory_types = {
   -1: L("Loss",       fr="Défaite",      de="Niederlage",   es="Derrota",                 it="Sconfitta",       ko="손실", pl="Porażka"),
    0: L("Time",       fr="Temps",        de="Zeit",         es="Victoria por tiempo",     it="A tempo",         ko="시간", pl="Czasowe"),
    1: L("Science",    fr="Scientifique", de="Wissenschaft", es="Ciencia",                 it="Scienza",         ko="과학", pl="Naukowe"),
    2: L("Domination", fr="Militaire",    de="Herrschaft",   es="Victoria por dominación", it="Per Dominazione", ko="정복", pl="Dominacja"),
    3: L("Cultural",   fr="Culturelle",   de="Kultur",       es="Victoria cultural",       it="Culturale",       ko="문화", pl="Kulturowe"),
    4: L("Diplomatic", fr="Diplomatique", de="Diplomatie",   es="Victoria diplomática",    it="Diplomatica",     ko="외교", pl="Dyplomatyczne"),
}

# advanced game options TXT_KEY_MP_OPTION_ALWAYS_PEACE and TXT_KEY_GAME_OPTION_* Still need ja and ru
game_options = {
    0: L("No City Razing",          fr="Impossible de raser les villes",       de="Keine Stadtvernichtung",                       es="Sin arrasar ciudades",           it="Nessuna possibilità di razziare le città",       ko="도시 파괴 불가",        pl="Bez niszczenia miast"),
    1: L("No Barbarians",           fr="Aucun barbare",                        de="Keine Barbaren",                               es="Sin bárbaros",                   it="No barbari",                                     ko="야만인 없음",           pl="Bez barbarzyńców"),
    2: L("Raging Barbarians",       fr="Barbares déchaînés",                   de="Wütende Barbaren",                             es="Bárbaros coléricos",             it="Barbari furiosi",                                ko="야만인 부흥",           pl="Inwazja barbarzyńców"),
    3: L("Always War",              fr="Guerre constante",                     de="Immer Krieg",                                  es="Siempre en guerra",              it="Sempre in guerra",                               ko="항상 전쟁 상태",        pl="Permanentna wojna"),
    4: L("Always Peace",            fr="Paix constante",                       de="Immer Frieden",                                es="Siempre en paz",                 it="Sempre in pace",                                 ko="항상 평화 상태",        pl="Wieczny pokój"),
    5: L("One-City Challenge",      fr="Ville unique",                         de="Einzelstadt-Wettkampf",                        es="Reto de una sola ciudad",        it="Sfida con una singola città",                    ko="단일 도시로 도전",      pl="Starcie pojedynczych miast"),
    6: L("Permanent War or Peace",  fr="Aucun changement guerre - paix",       de="Ständiger Krieg oder Frieden",                 es="Guerra o paz permanentes",       it="Guerra o pace permanenti",                       ko="영구적 전쟁 또는 평화", pl="Permanentna wojna lub pokój"),
    7: L("New Random Seed",         fr="Nouvelles valeurs aléatoires",         de="Zufallsgenerator",                             es="Nuevo valor de origen al azar",  it="Nuovo seme casuale",                             ko="무작위 시드",           pl="Losowa kalkulacja obrażeń"),
    8: L("Lock Mods",               fr="Verrouiller les mods",                 de="Mods sperren",                                 es="Bloquear \"mods\"",              it="Blocca Mod",                                     ko="모드 잠금",             pl="Blokada modów"),
    9: L("Complete Kills",          fr="Destruction totale",                   de="Komplette Vernichtung",                        es="Destrucción total",              it="Sterminio completo",                             ko="전멸전",                pl="Pełna eliminacja"),
   10: L("No Ancient Ruins",        fr="Pas de ruines antiques",               de="Keine Alten Ruinen",                           es="Sin Ruinas antiguas",            it="Nessuna Antica rovina",                          ko="고대 유적 없음",        pl="Bez starożytnych ruin"),
   11: L("Random Personalities",    fr="Personnalités aléatoires",             de="Zufällige Persönlichkeiten",                   es="Personalidades al azar",         it="Personalità casuale",                            ko="무작위 특성",           pl="Losowe usposobienie"),
   12: L("Allow Policy Saving",     fr="Autoriser l'économie de doctrines",    de="Ermöglicht das Speichern von Sozialpolitiken", es="Permitir guardarse política",    it="Permetti l'accumulo di Politiche",               ko="정책 저장 허용",        pl="Zezwalaj na zapisy z pol. społ."),
   13: L("Allow Promotion Saving",  fr="Autoriser l'économie de promotions",   de="Ermöglicht das Speichern von Beförderungen",   es="Permitir guardarse ascenso",     it="Permetti l'accumulo di promozioni",              ko="승급 저장 허용",        pl="Zezwalaj na zapisy z awansem"),
   14: L("Enable Turn Timer",       fr="Active le chrono. tour",               de="Rundenzähler aktivieren",                      es="Activa el contador del turno ",  it="Attiva il timer dei turni ",                     ko="턴 타이머 사용",        pl="Włącz stoper"),
   15: L("Quick Combat",            fr="Combat rapide",                        de="Schneller Kampf",                              es="Combate rápido",                 it="Combattimento rapido",                           ko="빠른 전투",             pl="Szybka walka"),
   16: L("Disable Start Bias",      fr="Désactiver les préférences de départ", de="Keine Startvorgaben",                          es="Desactivar disposición inicial", it="Disattiva posizionamento iniziale intelligente", ko="무작위 시작 위치",      pl="Start z losowym rozmieszczeniem"),
   17: L("Disable Research",        fr="Désactiver recherches",                de="Forschung ausschalten",                        es="Desactivar investigación",       it="Disattiva la Ricerca",                           ko="연구 비활성화",         pl="Wyłącz badania"),
   18: L("Disable Happiness",       fr="Désactiver bonheur",                   de="Zufriedenheit ausschalten",                    es="Desactivar Felicidad",           it="Disattiva la Felicità",                          ko="행복 비활성화",         pl="Wyłącz zadowolenie"),
   19: L("Disable Policies",        fr="Désactiver doctrines",                 de="Politiken ausschalten",                        es="Desactivar políticas",           it="Disattiva le Politiche",                         ko="정책 비활성화",         pl="Wyłącz ustroje"),
   20: L("Disable Tutorial Popups", fr="Désactiver la fonction didacticiel",   de="Tutorial-Popups deaktivieren",                 es="Desactivar tutoriales",          it="Disattiva i tutorial pop-up",                    ko="튜토리얼 팝업창 해제",  pl="Wyłącz pojawianie się podpowiedzi samouczka"),
}
option_noraze = 0;
option_occ = 5;

# the colour to use for city state owned tiles
citystate_color = ["#dddddd", "black"]

# civs we recognize
# replay files don't actually contain the name of the civ,
# so we guess from the first city's name...
# the player civ is an exception.
# MP Localization notes: some languages (mainly German and Polish) have multiple
# entries on their text keys and I have no idea which is correct so I have arbitrarily
# chosen the first on the list in each case.
civs = [
# Standard civs TXT_KEY_CIV_*_DESC and TXT_KEY_CITY_NAME_* Still need some ja and ru
    [ L("American Empire",fr="Empire américain",de="Amerikanisches Reich",es="Imperio Estadounidense",it="Impero Americano",ko="미국 제국",pl="Imperium amerykańskie",ja="アメリカ文明"), L("Washington",fr="Washington",de="Washington",es="Washington",it="Washington",ko="워싱턴",pl="Waszyngton",ja="ワシントン",ru="Вашингтон"), "#ffffff", "#1f3378" ],
    [ L("Arabian Empire",fr="Empire arabe",de="Arabisches Reich",es="Imperio Árabe",it="Impero Arabo",ko="아라비아 제국",pl="Imperium arabskie"), L("Mecca",fr="La Mecque",de="Mekka",es="La Meca",it="Mecca",ko="메카",pl="Mekka",ja="メッカ",ru="Мекка"), "#92dd09", "#2b572d" ],
    [ L("Aztec Empire",fr="Empire aztèque",de="Aztekenreich",es="Imperio Azteca",it="Impero Azteco",ko="아즈텍 제국",pl="Imperium Azteckie",ru="Ацтекская империя"), L("Tenochtitlan",fr="Tenochtitlan",de="Tenochtitlan",es="Tenochtitlán",it="Tenochtitlan",ko="테노치티틀란",pl="Tenochtitlan",ja="テノチティタラン",ru="Теночтитлан"), "#88eed4", "#a13922" ],
    [ L("Chinese Empire",fr="Empire chinois",de="Chinesisches Kaiserreich",es="Imperio Chino",it="Impero Cinese",ko="중국 제국",pl="Cesarstwo chińskie",ja="中国文明",ru="Китай"), L("Beijing",fr="Pékin",de="Peking",es="Pekín",it="Pechino",ko="북경",pl="Pekin",ja="北京",ru="Пекин"), "#ffffff", "#009452" ],
    [ L("Egyptian Empire",fr="Empire égyptien",de="Ägyptisches Reich",es="Imperio Egipcio",it="Impero Egizio",ko="이집트 제국",pl="Imperium egipskie"), L("Thebes",fr="Thèbes",de="Theben",es="Tebas",it="Tebe",ko="테베",pl="Teby",ja="テーベ",ru="Фивы"), "#5200d0", "#fffb03" ],
    [ L("English Empire",fr="Empire anglais",de="Englisches Reich",es="Imperio Inglés",it="Impero Inglese",ko="대영 제국",pl="Imperium angielskie"), L("London",fr="Londres",de="London",es="Londres",it="Londra",ko="런던",pl="Londyn",ja="ロンドン",ru="Лондон"), "#ffffff", "#6c0200" ],
    [ L("French Empire",fr="Empire français",de="Französisches Reich",es="Imperio Francés",it="Impero Francese",ko="프랑스 제국",pl="Imperium francuskie",ru="Франция"), L("Paris",fr="Paris",de="Paris",es="París",it="Parigi",ko="파리",pl="Paryż",ja="パリ",ru="Париж"), "#ebeb8a", "#418dfd" ],
    [ L("German Empire",fr="Empire allemand",de="Deutsches Reich",es="Imperio Alemán",it="Impero Tedesco",ko="독일 제국",pl="Cesarstwo niemieckie"), L("Berlin",fr="Berlin",de="Berlin",es="Berlín",it="Berlino",ko="베를린",pl="Berlin",ja="ベルリン",ru="Берлин"), "#242b20", "#b3b1b8" ],
    [ L("Greek Empire",fr="Empire grec",de="Griechisches Reich",es="Imperio Griego",it="Impero Greco",ko="그리스 제국",pl="Imperium greckie",ru="Греция"), L("Athens",fr="Athènes",de="Athen",es="Atenas",it="Atene",ko="아테네",pl="Ateny",ja="アテネ",ru="Афины"), "#418dfd", "#ffffff" ],
    [ L("Indian Empire",fr="Empire indien",de="Indisches Reich",es="Imperio Indio",it="Impero Indiano",ko="인도 제국",pl="Imperium indyjskie"), L("Delhi",fr="Delhi",de="Delhi",es="Delhi",it="Delhi",ko="델리",pl="Delhi",ja="デリー",ru="Дели"), "#ff9931", "#128706" ],
    [ L("Iroquois Empire",fr="Empire iroquois",de="Irokesisches Reich",es="Imperio Iroqués",it="Impero Irochese",ko="이로쿼이 제국",pl="Imperium Irokeskie",ru="Империя ирокезов"), L("Onondaga",fr="Onondaga",de="Onondaga",es="Onondaga",it="Onondaga",ko="오논다가",pl="Onondaga",ja="オノンダガ",ru="Онондага"), "#fbc981", "#415656" ],
    [ L("Japanese Empire",fr="Empire japonais",de="Japanisches Reich",es="Imperio Japonés",it="Impero Giapponese",ko="일본 제국",pl="Cesarstwo japońskie",ja="日本文明"), L("Kyoto",fr="Kyoto",de="Kyoto",es="Kioto",it="Kyoto",ko="교토",pl="Kioto",ja="京都",ru="Киото"), "#b80000", "#ffffff" ],
    [ L("Ottoman Empire",fr="Empire ottoman",de="Osmanisches Reich",es="Imperio Otomano",it="Impero Ottomano",ko="오스만 제국",pl="Imperium Osmańskie"), L("Istanbul",fr="Istanbul",de="Istanbul",es="Estambul",it="Istanbul",ko="이스탄불",pl="Stambuł",ja="イスタンブール",ru="Стамбул"), "#12521e", "#f7f8c7" ],
    [ L("Persian Empire",fr="Empire perse",de="Persisches Reich",es="Imperio Persa",it="Impero Persiano",ko="페르시아 제국",pl="Imperium perskie"), L("Persepolis",fr="Persépolis",de="Persepolis",es="Persépolis",it="Persepoli",ko="페르세폴리스",pl="Persepolis",ja="ペルセポリス",ru="Персеполис"), "#f5e637", "#b00703" ],
    [ L("Roman Empire",fr="Empire romain",de="Römisches Reich",es="Imperio Romano",it="Impero Romano",ko="로마 제국",pl="Imperium rzymskie"), L("Rome",fr="Rome",de="Rom",es="Roma",it="Roma",ko="로마",pl="Rzym",ja="ローマ",ru="Рим"), "#efc600", "#460076" ],
    [ L("Russian Empire",fr="Empire russe",de="Russisches Reich",es="Imperio Ruso",it="Impero Russo",ko="러시아 제국",pl="Imperium rosyjskie",ru="Российская империя"), L("Moscow",fr="Moscou",de="Moskau",es="Moscú",it="Mosca",ko="모스크바",pl="Moskwa",ja="モスクワ",ru="Москва"), "#000000", "#eeb400" ],
    [ L("Siamese Empire",fr="Empire siamois",de="Siamesisches Reich",es="Imperio Siamés",it="Impero del Siam",ko="시암 제국",pl="Imperium syjamskie",ru="Сиамская империя"), L("Sukhothai",fr="Sukhothaï",de="Sukhothai",es="Sukhothai",it="Sukhothai",ko="수고타이",pl="Sukhothai",ja="スコータイ",ru="Сукотай"), "#b00703", "#f5e637" ],
    [ L("Songhai Empire",fr="Empire songhaï",de="Songhai-Reich",es="Imperio de Songhai",it="Impero Songhai",ko="송가이 제국",pl="Imperium songhajskie",ru="Сонгайская империя"), L("Gao",fr="Gao",de="Gao",es="Gao",it="Gao",ko="가오",pl="Gao",ja="ガオ",ru="Гао"), "#5a0009", "#d59113" ],
# DLC civs
    [ L("Babylonian Empire",fr="Empire babylonien",de="Babylonisches Reich",es="Imperio Babilonio",it="Impero babilonese",ko="바빌론 제국",pl="Imperium babilońskie",ja="バビロニア文明",ru="Вавилонское царство"), L("Babylon",fr="Babylone",de="Babylon",es="Babilonia",it="Babilonia",ko="바빌론",pl="Babilon",ja="バビロン",ru="Вавилон"), "#c8f8ff", "#2b5161" ],
    [ L("Mongolian Empire",fr="Empire mongol",de="Mongolisches Reich",es="Imperio Mongol",it="Impero mongolo",ko="몽골 제국",pl="Imperium mongolskie",ja="モンゴル文明",ru="Монгольская империя"), L("Karakorum",fr="Karakorum",de="Karakorum",es="Karakorum",it="Karakorum",ko="카라코람",pl="Karakorum",ja="カラコルム",ru="Каракорум"), "#ff7800", "#510008" ],
    [ L("Spanish Empire",fr="Empire espagnol",de="Spanisches Reich",es="Imperio Español",it="Impero spagnolo",ko="스페인 제국",pl="Imperium hiszpańskie",ja="スペイン文明",ru="Испания"), L("Madrid",fr="Madrid",de="Madrid",es="Madrid",it="Madrid",ko="마드리드",pl="Madryt",ja="マドリッド",ru="Мадрид"), "#f4a8a8", "#531a1a" ],
    [ L("Incan Empire",fr="Empire inca",de="Inkareich",es="Imperio Inca",it="Impero Inca",ko="잉카 제국",pl="Imperium Inków",ja="インカ文明",ru="Империя инков"), L("Cusco",fr="Cuzco",de="Cusco",es="Cuzco",it="Cuzco",ko="쿠스코",pl="Cuzco",ja="クスコ",ru="Куско"), "#069f77", "#ffb821" ],
    [ L("Polynesian Empire",fr="Empire polynésien",de="Polynesisches Reich",es="Imperio Polinesio",it="Polinesia",ko="폴리네시아 제국",pl="Imperium polinezyjskie",ja="ポリネシア帝国",ru="Полинезия"), L("Honolulu",fr="Honolulu",de="Honolulu",es="Honolulú",it="Honolulu",ko="호놀룰루",pl="Honolulu",ja="ホノルル",ru="Гонолулу"), "#ffff4a", "#d95800" ],
    [ L("Danish Empire",fr="Empire danois",de="Dänisches Reich",es="Imperio Danés",it="Impero Danese",ko="덴마크 제국",pl="Imperium Duńskie",ja="デンマーク帝国",ru="Дания"), L("Copenhagen",fr="Copenhague",de="Kopenhagen",es="Copenhague",it="Copenhagen",ko="코펜하겐",pl="Kopenhaga",ja="コペンハーゲン",ru="Копенгаген"), "#efe7b3", "#6c2a14" ],
]

# colours for map features
map_colors = {
    "TERRAIN_GRASS":    "#b2d578",
    "TERRAIN_PLAINS":   "#e7c779",
    "TERRAIN_DESERT":   "#eedda3",
    "TERRAIN_TUNDRA":   "#bacac9",
    "TERRAIN_SNOW":     "#eaeaea",
    "TERRAIN_COAST":    "#7bbbde",
    "TERRAIN_OCEAN":    "#7cadc8",
    "TERRAIN_MOUNTAIN": "#575757",
    "TERRAIN_HILL":     "#000000",
}

# Characters to be replaced before putting otherwise unsanitized text in HTML
html_escape = {
    "&":    "&amp;",
    "<":    "&lt;",
    ">":    "&gt;",
    '"':    "&quot;",
}

#
# HTML code to describe the map area and the event list.
# Instance variables of the Civ5Replay object are available 
# via %(variable name)s as per normal python string formatting
# rules. The "id" variable is a reasonably unique identifier,
# so that multiple HTML replays can be embedded in the same
# web page.
#
# Note that % characters have to be escaped as %%.
#
html_header = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>
    %(leader_name)s
    %(l_of_the)s%(civ_name)s 
    (%(difficulty)s, %(map_name)s, %(map_size)s, %(final_turn)s %(l_turns_played)s)
</title>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
"""
html_footer = """
</body>
</html>
"""

html_skeleton = """
<style type="text/css"><!--

div#%(id)s_main {
    display: table;
    border: 1px solid #333333;
}

div#%(id)s_gameinfo { 
    background: #333333;
    color: white;
    text-align: center;
    padding: 4px;
}

div#%(id)s_canvas { 
    position: absolute;
    z-index: 0;
}

div#%(id)s_overlay { 
    position: absolute;
    z-index: 10;
    padding: 4px;
    color: #555555;
    font-size: 80%%;
}

div#%(id)s_signs { 
    position: absolute;
    z-index: 1;
}

div.%(id)s_sign {
    position: absolute;
    opacity: 0.5;
    white-space: nowrap;
    font-size: 60%%;
    font-family: Helvetica;
    font-stretch: condensed;
    padding: 2px;
    z-order: 3;
}

div.%(id)s_sign_text {
    position: absolute;
    white-space: nowrap;
    font-size: 60%%;
    font-family: Helvetica;
    font-stretch: condensed;
    padding: 2px;
    background: transparent;
    z-order: 5;
}

div#%(id)s_controls {
    background: #666655;
    color: white;
    padding: 4px;
    font-size: 80%%;
}

div#%(id)s_log {
    background: #333333;
    color: white;
    height: 300px;
    overflow-y: scroll;
}

a.%(id)s_button {
    background: #333333;
    border: 1px solid black;
    padding-left: 10px;
    padding-right: 10px;
    cursor: pointer;
}

a.%(id)s_button:active {
    background: #555555;
}

span#%(id)s_turncounter {
    float: right;
}

td.%(id)s_base_turn {
    font-size: 80%%;
    padding-left: 0px;
    padding-top: 0px;
    padding-bottom: 0px;
    padding-right: 20px;
}

td.%(id)s_base_text {
    font-size: 80%%;
    padding: 0px;
}

td.%(id)s_event_turn {
    color: #aaaaaa;
}

td.%(id)s_event_text {
    color: #dddddd;
}

span#%(id)s_title {
    font-size: 150%%;
}

span#%(id)s_subtitle {
    font-size: 80%%;
}

span.%(id)s_disabled_option {
    text-decoration: line-through;
}

--></style>

</head>
<body>

<div id="%(id)s_main">
    <div id="%(id)s_gameinfo">
        <span id="%(id)s_title">
            %(leader_name)s
            %(l_of_the)s%(civ_name)s 
        </span><br/>
        <span id="%(id)s_subtitle">
            %(difficulty)s | %(map_name)s | %(map_size)s |%(options_pipe)s %(final_turn)s %(l_turns_played)s
            <br/>
            %(l_In)s %(final_year)s, %(victory_text)s
        </span>
    </div>
    <div id="%(id)s_map">
        <div id="%(id)s_overlay">If you see this, something didn't work.</div>
        <div id="%(id)s_signs"></div>
        <canvas id="%(id)s_canvas" width="%(html_w)d" height="%(html_h)d"></canvas>
    </div>
    <div id="%(id)s_controls" onselectstart="return false">
        <a class="%(id)s_button" onclick="%(id)s_restart_animation()" onselectstart="return false">|&lt;</a>
        <a class="%(id)s_button" onclick="%(id)s_frame(-10)" onselectstart="return false">&lt;&lt;</a>
        <a class="%(id)s_button" onclick="%(id)s_frame(-1)" onselectstart="return false">&lt;</a>
        <a class="%(id)s_button" onclick="%(id)s_toggle_animation()" onselectstart="return false">&#x25a0;</a>
        <a class="%(id)s_button" onclick="%(id)s_frame(1)" onselectstart="return false">&gt;</a>
        <a class="%(id)s_button" onclick="%(id)s_frame(10)" onselectstart="return false">&gt;&gt;</a>
        <a class="%(id)s_button" onclick="%(id)s_frame(99999)" onselectstart="return false">&gt;|</a>
        
        &nbsp;&nbsp;&nbsp;&nbsp;
        
        <a class="%(id)s_button" onclick="%(id)s_toggle_alpha()" onselectstart="return false">&#945;</a>
       
        &nbsp;&nbsp;&nbsp;&nbsp;
        &nbsp;&nbsp;&nbsp;&nbsp;
        &nbsp;&nbsp;&nbsp;&nbsp;

        <a class="%(id)s_button" onclick="%(id)s_show_histogram()" onselectstart="return false">score</a>
        
        <span id="%(id)s_turncounter">error</span>
    </div>
    <div id="%(id)s_log">
        %(html_event_list)s
    </div>
</div>
"""

#
# All the static javascript code used to animate the map.
#
html_javascript = """
<script type="text/javascript"><!--

var %(id)s_c;
var %(id)s_last_turn_drawn = -1;
var %(id)s_refresh = 0;

var %(id)s_max_turn = %(final_turn)d;
var %(id)s_events = %(javascript_event_list)s;
var %(id)s_turn_to_event = %(javascript_turn_to_event)s;
var %(id)s_background = %(javascript_background)s;
var %(id)s_domain = [];

var %(id)s_civs = %(javascript_civs)s;

var %(id)s_histogram_w = %(histogram_w)d;
var %(id)s_histogram_h = %(histogram_h)d;
var %(id)s_histogram_scale_w = %(histogram_scale_w)f;
var %(id)s_histogram_scale_h = %(histogram_scale_h)f;
var %(id)s_histogram = %(javascript_histogram_score)s;

var %(id)s_timeout = null;

var %(id)s_border_alpha = 0.2;

// Set up the canvas and the other HTML areas
function %(id)s_setup() {
    var canvas = document.getElementById('%(id)s_canvas');
    if(canvas.getContext) {
        canvas = canvas.getContext("2d");
        %(id)s_c = canvas;
    }
    if(%(id)s_background.length <= 0) {
        %(id)s_border_alpha = 1.0;
    }
    %(id)s_render_turn(%(start_turn)d);
    %(id)s_advance_turn();
}

// Toggle alpha
function %(id)s_toggle_alpha() {
    var ba = %(id)s_border_alpha;
    if(ba < 0.5) {
        ba = 1.0;
    } else if(ba < 0.9) {
        ba = 0.2;
    } else {
        ba = 0.6;
    }
    %(id)s_border_alpha = ba;
    %(id)s_refresh = 1;
    if(%(id)s_timeout === null) {
        %(id)s_stop_animation();
    }
}

// Stop the animation
function %(id)s_stop_animation() {
    var turn = %(id)s_last_turn_drawn;
    %(id)s_render_turn(turn);
    if(%(id)s_timeout === null) return;
    clearTimeout(%(id)s_timeout);
    %(id)s_timeout = null;
}

// Toggle playback
function %(id)s_toggle_animation() {
    if(%(id)s_timeout === null) %(id)s_advance_turn();
    else %(id)s_stop_animation();
}

// Switch to histogram
function %(id)s_show_histogram() {
    %(id)s_stop_animation();
    document.getElementById("%(id)s_signs").style.display = "none";
    %(id)s_draw_histogram(%(id)s_histogram, %(id)s_histogram_scale_w, %(id)s_histogram_scale_h);
    %(id)s_refresh = 1;
}

// Restart the animation from turn 0
function %(id)s_restart_animation() {
    %(id)s_last_turn_drawn = -1;
    %(id)s_advance_turn();
}

// Advance x frames
function %(id)s_frame(x) {
    x = %(id)s_last_turn_drawn + x;
    if(x < %(start_turn)d) x = %(start_turn)d;
    if(x > %(id)s_max_turn) x = %(id)s_max_turn;
    %(id)s_refresh = 1;
    %(id)s_render_turn(x);
}

// Draw the next turn and set up a timer to continue the animation
function %(id)s_advance_turn() {
    if(%(id)s_timeout !== null) {
        clearTimeout(%(id)s_timeout);
        %(id)s_timeout = null;
    }
    turn = %(id)s_last_turn_drawn + 1;
    if(turn == 0) turn = %(start_turn)d;
    %(id)s_render_turn(turn);
    if(turn >= %(id)s_max_turn) {
        return;
    }
    %(id)s_timeout = setTimeout(%(id)s_advance_turn, 100);
}

// Find a neighbour sharing a given border with a hex tile
function %(id)s_neighbour(x, y, b) {
    var x2 = x;
    var y2 = y;
    var xoff = 1-(y%%2);
    switch(b) {
    case 0:
        x2 = x+xoff;
        y2 = y-1;
        break;
    case 1:
        x2 = x+1;
        y2 = y;
        break;
    case 2:
        x2 = x+xoff;
        y2 = y+1;
        break;
    case 3:
        x2 = x+xoff-1;
        y2 = y+1;
        break;
    case 4:
        x2 = x-1;
        y2 = y;
        break;
    case 5:
        x2 = x+xoff-1;
        y2 = y-1;
        break;
    }
    return [x2, y2];
}

// Determine if a border between tiles is internal to the empire
function %(id)s_is_inside(x, y, b) {
    var pos = %(id)s_neighbour(x, y, b);
    x2 = pos[0]; y2 = pos[1];
    if(x2 == x && y2 == y) return 1;
    if(x2 < 0 || y2 < 0 || x2 >= %(w)d || y2 >= %(h)d) return 0;
    d1 = %(id)s_domain[y][x];
    d2 = %(id)s_domain[y2][x2];
    if(!d1 || !d2) return 0;
    if(d1[0] == d2[0] && d1[1] == d2[1]) return 1;
    return 0;
}

// Remove all signs
function %(id)s_reset_signs() {
    var parent = document.getElementById("%(id)s_signs");
    while(parent.childNodes.length >= 1) {
        parent.removeChild(parent.firstChild);
    }
}

// Put up a signpost
function %(id)s_set_sign(x, y, bg, fg, text) {
    var parent = document.getElementById("%(id)s_signs");
    parent.style.display = "block";
    var id = "%(id)s_"+x+"_"+y;
    var sign = document.getElementById(id);
    if(sign) parent.removeChild(sign);
    var stext = document.getElementById(id+"_text");
    if(stext) parent.removeChild(stext);
    if(text == "") return;
    x = x * 1.0;
    y = y * 1.0;
    if((%(h)d-y)%%2 == 0) {
        x += 0.5;
    }
    s = %(tile_size)f;
    x = s * (x + 1.5);
    y = (2*s/3) * (y + 0.5);
    sign = document.createElement("div");
    sign.setAttribute("id", id);
    sign.setAttribute("class", "%(id)s_sign");
    sign.setAttribute("style", "left: "+x+"px; top: "+y+"px; background: "+bg+"; color: "+fg+";");
    sign.innerHTML = text;
    parent.appendChild(sign);
    stext = document.createElement("div");
    stext.setAttribute("id", id+"_text");
    stext.setAttribute("class", "%(id)s_sign_text");
    stext.setAttribute("style", "left: "+x+"px; top: "+y+"px; color: "+fg+";");
    stext.innerHTML = text;
    parent.appendChild(stext);
}

// Draw the map as of a given turn
function %(id)s_render_turn(turn) {
    if(turn < 0) {
        turn = 0;
    }
    if(%(id)s_refresh) {
        %(id)s_refresh = 0;
        %(id)s_last_turn_drawn = -1;
    }
    var txt = [];
    if(%(id)s_last_turn_drawn < 0 || %(id)s_last_turn_drawn > turn) {
        %(id)s_reset_signs();
        %(id)s_c.fillStyle = "rgb(220,220,180)";
        %(id)s_c.fillRect(0, 0, %(html_w)d, %(html_h)d);
        if(%(id)s_background.length > 0) {
            for(var y=0; y<%(h)d; ++y) {
                if(y >= %(id)s_background.length) break;
                for(var x=0; x<%(w)d; ++x) {
                    if(x >= %(id)s_background[y].length) break;
                    bg = %(id)s_background[y][x][0];
                    hf = %(id)s_background[y][x][1];
                    rf = %(id)s_background[y][x][2];
                    %(id)s_draw_hex_tile(x, y, bg, "", 0, hf, rf);
                }
            }
        }
        %(id)s_domain = Array(%(h)d);
        for(var y=0; y<=%(h)d; ++y) {
            %(id)s_domain[y] = Array(%(w)d+1);
        }
    }
    var start = 0;
    if(%(id)s_last_turn_drawn < turn && %(id)s_last_turn_drawn >= 0) {
        start = %(id)s_turn_to_event[turn];
    }
    var c = %(id)s_c;
    tiles = {};
    for(var i=start; i<%(id)s_events.length; ++i) {
        evt = %(id)s_events[i];
        if(evt[0] > turn) {
            break;
        }
        if(evt[0] == turn && evt[5] != "") {
            txt.push(evt[5]);
        }
        if(evt[3] != "") {
            var x = evt[1];
            var y = evt[2];
            dom = %(id)s_domain[y][x]
            if(dom) {
                if(evt[6] == 1 && evt[7] == "") {
                    evt[7] = dom[3];
                }
            }
            %(id)s_domain[y][x] = [evt[3], evt[4], evt[6], evt[7]];
            tiles[""+x+","+y] = [x, y];
            for(var j=0; j<6; ++j) {
                var pos = %(id)s_neighbour(x, y, j);
                if(pos[0] < 0 || pos[1] < 0 || pos[0] >= %(w)d || pos[1] >= %(h)d) continue;
                tiles[""+pos[0]+","+pos[1]] = pos;
            }
        }
    }
    for(var i in tiles) {
        t = tiles[i];
        x = t[0];
        y = t[1];
        d = %(id)s_domain[y][x];
        if(%(id)s_background.length > 0) {
            %(id)s_draw_hex_tile(x, y, %(id)s_background[y][x][0], "", 0, %(id)s_background[y][x][1], %(id)s_background[y][x][2]);
        } else {
            %(id)s_draw_hex_tile(x, y, "rgb(220,220,180)", "", 0, 0, 0);
        }
        if(!d) continue;
        if(%(id)s_background.length <= 0) {
            %(id)s_draw_hex_tile(x, y, d[0], "", 0, 0, 0, %(id)s_border_alpha);
        } else { 
            %(id)s_draw_hex_tile(x, y, d[0], "", 0, 0, 0, %(id)s_border_alpha);
        }
        borders = [];
        for(var j=0; j<6; ++j) {
            if(%(id)s_is_inside(x, y, j)) continue;
            borders.push([x,y,j]);
        }
        if(borders.length > 0) {
            for(var j=0; j<borders.length; ++j) {
                %(id)s_draw_hex_border(borders[j][0], borders[j][1], d[0], borders[j][2], 0);
            }
            for(var j=0; j<borders.length; ++j) {
                %(id)s_draw_hex_border(borders[j][0], borders[j][1], d[1], borders[j][2], 1); 
            }
        }
        if(d[2] <= 0) {
            %(id)s_set_sign(x, y, "", "", "");
        } else if(d[2] == 1) {
            if(d[3] != "") %(id)s_set_sign(x, y, d[0], d[1], d[3]);
            %(id)s_draw_city(x, y, d[0], d[1]);
        }
    }
    html = "";
    for(var t in txt) {
        t = txt[t];
        html += t + "<br/>";
    }
    overlay = document.getElementById("%(id)s_overlay");
    overlay.style.display = "block";
    if(html != "") {
        html = "%(l_Turn)s " + turn + "<br/>" + html;
        overlay.innerHTML = html;
    }
    turncounter = document.getElementById("%(id)s_turncounter");
    if(turn > %(id)s_max_turn) {
        turncounter.innerHTML = %(id)s_max_turn;
    } else {
        turncounter.innerHTML = turn;
    }
    %(id)s_last_turn_drawn = turn;
}

// Draw a city symbol
function %(id)s_draw_city(x, y, bg, fg) {
    var c = %(id)s_c;
    x = x * 1.0;
    y = y * 1.0;
    if((%(h)d-y)%%2 == 0) {
        x += 0.5;
    }
    s = %(tile_size)f;
    x = s * (x + 0.5);
    y = (2*s/3) * (y + 0.5);
    c.beginPath();
    c.arc(x+s/2, y+s/2, s/4, 0, Math.PI*2, true);
    c.fillStyle = bg;
    c.fill();
    c.beginPath();
    c.arc(x+s/2, y+s/2, s/6, 0, Math.PI*2, true);
    c.fillStyle = fg;
    c.fill();
}

// Draw a single border
function %(id)s_draw_hex_border(x, y, col, b, outer) {
    var c = %(id)s_c;
    x = x * 1.0;
    y = y * 1.0;
    if((%(h)d-y)%%2 == 0) {
        x += 0.5;
    }
    s = %(tile_size)f;
    x = s * (x + 0.5);
    y = (2*s/3) * (y + 0.5);
    switch(b) {
    case 0:
        xo1 = x+s/2;
        yo1 = y;
        xo2 = x+s;
        yo2 = y+s/3;
        xi1 = xo1-s/8;
        yi1 = yo1+s/12;
        xi2 = xo2;
        yi2 = yo2+s/6;
        break;
    case 1:
        xo1 = x+s;
        yo1 = y+s/3;
        xo2 = x+s;
        yo2 = y+2*s/3;
        xi1 = xo1-s/9;
        yi1 = yo1-s/12;
        xi2 = xo2-s/9;
        yi2 = yo2+s/12;
        break;
    case 2:
        xo1 = x+s;
        yo1 = y+2*s/3;
        xo2 = x+s/2;
        yo2 = y+s;
        xi1 = xo1;
        yi1 = yo1-s/6;
        xi2 = xo2-s/8;
        yi2 = yo2-s/12;
        break;
    case 3:
        xo1 = x;
        yo1 = y+2*s/3;
        xo2 = x+s/2;
        yo2 = y+s;
        xi1 = xo1;
        yi1 = yo1-s/6;
        xi2 = xo2+s/8;
        yi2 = yo2-s/12;
        break;
    case 4:
        xo1 = x;
        yo1 = y+s/3;
        xo2 = x;
        yo2 = y+2*s/3;
        xi1 = xo1+s/9;
        yi1 = yo1-s/12;
        xi2 = xo2+s/9;
        yi2 = yo2+s/12;
        break;
    case 5:
        xo1 = x+s/2;
        yo1 = y;
        xo2 = x;
        yo2 = y+s/3;
        xi1 = xo1+s/8;
        yi1 = yo1+s/12;
        xi2 = xo2;
        yi2 = yo2+s/6;
        break;
    default:
        return;
    }
    xm1 = (xo1+xi1)/2;
    ym1 = (yo1+yi1)/2;
    xm2 = (xo2+xi2)/2;
    ym2 = (yo2+yi2)/2;
    c.fillStyle = col;
    c.beginPath();
    if(outer == 0) {
        c.moveTo(xo1, yo1);
        c.lineTo(xo2, yo2);
        c.lineTo(xi2, yi2);
        c.lineTo(xi1, yi1);
    } else {
        c.moveTo(xo1, yo1);
        c.lineTo(xo2, yo2);
        c.lineTo(xm2, ym2);
        c.lineTo(xm1, ym1);
    }
    c.fill();
}

// Draw a single hex tile
// tx, ty - position
// bg, fg - background and foreground colour if applicable
// et - marker flag, 1 = city dot
// hf - hill flag, 1 = hill, 2 = mountain, -1 = ice
// rf - river bitfield, 1 = right, 2 = bottom right, 4 = bottom left
// bgalpha, fgalpha - background and foreground alpha values
function %(id)s_draw_hex_tile(tx, ty, bg, fg, et, hf, rf, bgalpha, fgalpha) {
    if(typeof(bgalpha) == 'undefined') bgalpha = 1.0;
    if(typeof(fgalpha) == 'undefined') fgalpha = 1.0;
    var c = %(id)s_c;
    c.save();
    c.lineWidth = 2;
    var x = tx * 1.0;
    var y = ty * 1.0;
    if((%(h)d-y)%%2 == 0) {
        x += 0.5;
    }
    s = %(tile_size)f;
    x = s * (x + 0.5);
    y = (2*s/3) * (y + 0.5);
    c.fillStyle = bg;
    c.beginPath();
    c.moveTo(x+s/2, y);
    c.lineTo(x+s, y+s/3);
    c.lineTo(x+s, y+2*s/3);
    c.lineTo(x+s/2, y+s);
    c.lineTo(x, y+2*s/3);
    c.lineTo(x, y+s/3);
    c.lineTo(x+s/2, y);
    c.globalAlpha = bgalpha;
    c.fill();
    c.globalAlpha = fgalpha;
    if(fg != "") {
        c.strokeStyle = fg;
        c.stroke();
    }
    if(et == 1) {
        c.fillStyle = fg;
        c.beginPath();
        c.arc(x+s/2, y+s/2, s/4, 0, Math.PI*2, true);
        c.fill();
    }
    if(hf == -1) { // ice
        c.strokeStyle = "#ffffff";
        c.globalAlpha = 0.7;
        c.beginPath();
        c.moveTo(x+2*s/6, y+3*s/5);
        c.lineTo(x+4*s/6, y+3*s/5);
        c.moveTo(x+3*s/6, y+2*s/5);
        c.lineTo(x+5*s/6, y+2*s/5);
        c.stroke();
    } else if(hf == 1) { // hill
        c.strokeStyle = "#000000";
        c.globalAlpha = 0.1;
        c.beginPath();
        c.moveTo(x+s/7, y+8*s/12);
        c.lineTo(x+2*s/7, y+6*s/12);
        c.lineTo(x+3*s/7, y+8*s/12);
        c.moveTo(x+4*s/7, y+7*s/12);
        c.lineTo(x+5*s/7, y+5*s/12);
        c.lineTo(x+6*s/7, y+7*s/12);
        c.stroke()
    } else if(hf == 2) { // mountain
        c.strokeStyle = "#000000";
        c.globalAlpha = 0.3;
        c.beginPath();
        c.moveTo(x+s/7, y+5*s/7);
        c.lineTo(x+2*s/7, y+3*s/7);
        c.lineTo(x+3*s/7, y+5*s/7);
        c.moveTo(x+4*s/7, y+4*s/7);
        c.lineTo(x+5*s/7, y+2*s/7);
        c.lineTo(x+6*s/7, y+4*s/7);
        c.stroke()
    }

    if((rf & 7) != 0) {
        c.globalAlpha = 1.0;
        if( (rf & 1) == 1) { // river on the right
            %(id)s_draw_hex_border(tx, ty, "#7bbdde", 1, 1);
        }
        if( (rf & 2) == 2) { // river on bottom right
            %(id)s_draw_hex_border(tx, ty, "#7bbdde", 2, 1);
        }
        if( (rf & 4) == 4) { // river on bottom left
            %(id)s_draw_hex_border(tx, ty, "#7bbdde", 3, 1);
        }
    }
    c.restore();
}

// Draw a histogram
function %(id)s_draw_histogram(hdata, sx, sy) {
    overlay = document.getElementById("%(id)s_overlay");
    overlay.style.display = "none";
    %(id)s_c.fillStyle = "rgb(220,220,180)";
    %(id)s_c.fillRect(0, 0, %(html_w)d, %(html_h)d);

    x = 0;
    for(var h in hdata) {
        h = hdata[h];
        y = %(html_h)d; n = 0;
        for(var s in h) {
            s = h[s];
            st = s/9;
            for(var tt=0; tt<9; ++tt) {
                %(id)s_c.fillStyle = %(id)s_civs[n][2+(tt%%2)];
                %(id)s_c.fillRect(x, y-s*sy/9.0, 2*sx, s*sy/9.0);
                y -= s*sy/9.0;
            }
            n += 1;
        }
        x += sx;
    }
}

// Make sure our setup code runs when the page has loaded
if(window.addEventListener) {
    addEventListener("load", %(id)s_setup, false);
} else {
    attachEvent("onload", %(id)s_setup);
}

--></script>
"""

class Civ5FileReader(object):
    """ Some basic functionality for reading data from Civ 5 files. """

    def __init__(self, input):
        if isinstance(input, str):
            input = file(input, "rb")
        self.r = input

    def read_byte(self):
        """ Read a single byte as an integer value """
        t = self.r.read(1)
        if len(t) != 1:
            self.eof = True
            return 0
        return ord(t)

    def read_int(self):
        """ Read a single little endian 4 byte integer """
        # My *guess* is that they're all signed
        t = self.r.read(4)
        if len(t) != 4:
            self.eof = True
            return 0
        return struct.unpack("<i", t)[0]

    def read_ints(self, count=None, esize=1):
        """ Read count tuples of esize little endian 4 byte integers and return them in a list. If count is omitted, read it as a 4 byte integer first """
        if count is None:
            count = self.read_int()
        list = []
        while count > 0:
            if esize > 1:
                t = []
                for i in range(esize):
                    t.append(self.read_int())
                list.append(tuple(t))
            else:
                list.append(self.read_int())
            count -= 1
        return list

    def read_string(self):
        """ Read an undelimited string with the length given in the first 4 bytes """
        return self.r.read(self.read_int()).decode("utf-8", 'replace')

    def read_terminated_string(self):
        """ Read a nul-terminated string. """
        s = ""
        while True:
            c = self.r.read(1)
            if ord(c) == 0:
                return s.decode("utf-8", 'replace')
            s += c
    
    def read_terminated_string_list(self):
        """ Read a list of nul-terminated strings, terminated by a zero-length string. """
        l = []
        while True:
            s = self.read_terminated_string().decode("utf-8", 'replace')
            if s == "":
                return l
            l.append(s)

    def read_sized_string_list(self, size):
        """ Read a block of data with a given size, and split in null-terminated strings. """
        block = self.r.read(size)
        if block.endswith("\0"):
            block = block[:-1]
        return block.split("\0")

class Civ5Map(Civ5FileReader):
    """ Encapsulates a Civ V map, and can load Civ5Map files. """

    def __init__(self, input):
        Civ5FileReader.__init__(self, input)
        
        # map dimensions
        self.w = 0
        self.h = 0

        self.load_file(self.r)

    def load_file(self, f):
        """ Loads a Civ5Map file from a stream. """

        self.r = f
        
        first_byte = self.read_byte()   # type/version indicator
        self.is_scenario = first_byte & 0x80
        self.map_version = first_byte & 0x0f

        # width and height
        self.w = self.read_int()
        self.h = self.read_int()

        f.read(1)   # no idea

        self.read_int() # no idea
        terrain_len = self.read_int()  # length of terrain XML id block in bytes
        feat1_len = self.read_int()    # length of first feature block
        feat2_len = self.read_int()    # length of second feature block
        resource_len = self.read_int() # length of resource block
        self.read_int() # no idea
        string1_len = self.read_int()  # length of first string after id blocks
        string2_len = self.read_int()  # length of second string after id blocks

        # terrain/feature/resource identifiers as in XML
        self.terrains = self.read_sized_string_list(terrain_len)
        self.features = self.read_sized_string_list(feat1_len)
        f.read(feat2_len)
        self.resources = self.read_sized_string_list(resource_len)

        # for exported maps, the name will be the filename (w/o extension) and description will be blank
        self.map_name = f.read(string1_len)
        self.map_description = f.read(string2_len)

        # new string for version 0xb and later
        if (self.map_version >= 0x0b):
            string3_len = self.read_int()
            f.read(string3_len)

        self.map = []
        debugout = []
        for y in range(self.h):
            self.map.insert(0, [])
            if debug:
                debugout.insert(0, "")
            for x in range(self.w):
                tf = struct.unpack("bbbbbbbb", f.read(8))
                if debug:
                    if tf[4] == 2:
                        debugout[0] += 'M' # mountain
                    elif tf[4] == 1:
                        debugout[0] += self.get_terrain(tf[0])[8]
                    else:
                        debugout[0] += self.get_terrain(tf[0])[8].lower()
                # terrain id, resource id, feature id, hill flag, river flag
                self.map[0].append( (self.get_terrain(tf[0]), self.get_resource(tf[1]), self.get_feature(tf[2]), tf[4], tf[3]) )
        if debug:
            sys.stdout.write("\n".join(debugout)+"\n")

    def get_terrain(self, id):
        return self.terrains[id]

    def get_resource(self, id):
        return self.resources[id]

    def get_feature(self, id):
        return self.features[id]

    def map_info(self):
        """ Provide some basic human-readable description of the map. """
        return "%d x %d" % (self.w, self.h)

class Civ5ReplayEvent(object):
    """ Encapsulates a single event in a replay. """

    def __init__(self, event_data, event_text, is_last=False):
        # every event appears to start with 0xffffffff
        self.data = event_data
        self.text = event_text
        
        # record_type appears to be either 1 (an event) or 0 (final entry with the map data)
        self.record_type = self.data[0]
       
        # the following fields are only valid for type 0 records
        if self.record_type == 0 or is_last:
            self.start_turn = self.record_type
            self.record_type = 0

            # The starting year, BC is negative
            self.start_year = self.data[1]

            # The final turn count
            self.turn = self.data[2]

            # be nice to unsuspecting users
            self.event_type = 0
            self.x = -1
            self.y = -1
            self.civ = 0

        elif self.record_type == 1:
            # the following fields are only valid for type 1 records
            # the turn number the event happens on, 0 is initial setup 
            self.turn = self.data[1]

            # event type seems to be one of the following values:
            #  0    general information
            #  1    city founded
            #  2    culture gained 
            self.event_type = self.data[2]

            # map tile where the event happened, note that -1 are valid for events
            # not tied to a specific map tile (e.g. declarations of war)
            self.x = self.data[3]
            self.y = self.data[4]

            # which player this event is from, starting with 1; city states are all -1
            self.civ = self.data[5]

        # helpers
        self.city_name = None
        self.city = 0
        self.last_event = False

    def set_last_event(self, b):
        """ Mark this event as the last event in the replay """
        self.last_event = b

    def is_last_event(self):
        """ Return True if this is the last event in the replay """
        if self.last_event:
            return True
        return self.record_type == 0

    def update_map(self, lst):
        """ Update a list of lists with any map change stored in this event """
        if self.x < 0 or self.y < 0:
            return
        while len(lst) <= self.y:
            lst.append([])
        ln = lst[self.y]
        while len(ln) <= self.x:
            ln.append(0)
        if self.event_type == 1:
            ln[self.x] = -2
        else:
            if self.civ < 0:
                ln[self.x] = self.civ
            else:
                if ln[self.x] == -2:
                    return
                ln[self.x] = self.civ + 1

    def update_domain(self, lst):
        """ Update a list of lists of dictionaries with ownership changes """
        if self.x < 0 or self.y < 0:
            return
        while len(lst) <= self.y:
            lst.append([])
        ln = lst[self.y]
        while len(ln) <= self.x:
            ln.append({})
        d = ln[self.x]
        d[self.turn] = [ self.turn, self.civ, self.city, self.city_name ]

    def __str__(self):
        ret = u""
        if debug:
            ret = u"%-24s %02d %-20s " % (self.data, self.city, "[%s]"%(self.city_name,))
        if self.record_type == 0:
            ret += L("[Turn %d] Game ends after %d turns in %s", fr="[Tour %d] Le jeu a pris fin après %d tours en %s") % (self.turn, self.turn, self.text)
        else:
            ret += L("[Turn %d] %s",fr="[Tour %d] %s",de="[Runde %d] %s",es="[Turno %d] %s",it="[Turno %d] %s",ko="[턴 %d] %s",pl="[Tura %d] %s") % (self.turn, self.text)

        return ret

class Civ5Replay(Civ5FileReader):
    """ Provides access to data and sequential events in a replay file. """

    def __init__(self, input):
        Civ5FileReader.__init__(self, input)

        # Localized strings and regexps
        self.l_In = L("In", fr="En")
        self.l_of_the = L("of the ", fr="de l'")
        self.l_turns_played = L("turns played", fr="tours de jeu")
        # TXT_KEY_TIME_TURN
        self.l_Turn = L("Turn",fr="Tour",de="Runde",es="Turno",it="Turno",ko="턴",pl="Tura")
        # TXT_KEY_GAME_WON ja, ru guessed from replays
        self.l_victory = L(" has won ",fr=" a remporté ",de=" hat den Sieg in der Kategorie ",es=" ha conseguido una ",it=" ha riportato una vittoria ",ko=" 승리를 거두었습니다",pl=" wygrywa przez Zwycięstwo ",ja="勝利を収めた",ru=" одерживает ")
        # TXT_KEY_MISC_CITY_IS_FOUNDED ; ja (が建設されました。/が創設された。) and ru guessed from replays
        self.l_founded_str= L(" is founded.",fr=" fondée !",de=" wurde gegründet.",es="Se funda ",it=" è fondata.",ko="이(가) 건설되었습니다.",pl="Powstaje ",ja="設され",ru="Основан город")
        self.l_founded_re = L("(.*) is founded.",fr="(.*) fondée !",de="Die Stadt (.*) wurde gegründet.",es="Se funda (.*).",it="(.*) è fondata.",ko="(.*)이(가) 건설되었습니다.",pl="Powstaje (.*).",ja="(.*)が.設され.*た。",ru="Основан город (.*).")
        self.l_founded_comp = None
        # TXT_KEY_MISC_CITY_RAZED_BY ja, ru guessed from replays
        self.l_razed = L(" was set ablaze by ",fr=" incendié ",de=" in Brand gesteckt",es=" ha sido arrasada por el ",it=" è stata messa a ferro e fuoco dall",ko="(으)로 인해 불바다가 되었습니다",pl=" podpala ",ru=" огню город ")
        # TXT_KEY_MISC_CITY_WAS_CAPTURED_BY ja, ru guessed from replays
        self.l_captured = L(" was captured by ",fr=" pris ",de=" eingenommen",es=" ha capturado ",it=" è stata catturata dall",ko="에 점령당했습니다",pl=" zdobywa ",ja="に占領されました",ru=" захвачен державой ")

        # Initialize game information
        self.leader_name = None
        self.civ_name = None
        self.civ_name_short = None
        self.civ_name_possessive = None
        self.civs = []
        self.map_script = None
        self.map_size_id = None
        self.map_size = None
        self.start_year = None
        self.start_turn = None
        self.final_turn = None
        self.final_year = None
        self.victory_text = ""
        self.victory_type = None
        self.w = 0
        self.h = 0
        self.histogram = None
        self.histogram_w = 0
        self.histogram_h = 0

        # setup information
        self.victory_types = None
        self.game_options = None
        self.occ = False
        self.noraze = False

        # Initialize internal state
        self.background = None
        self.events = []
        self.map = []
        self.domain = []
        self.fully_read = False
        self.eof = False
        self.cities = {}
        self.citystates = {}
        self.razed = []
        self.captured = {}

        # Initiailze variables for HTML output
        self.id = "replay_" + str(uuid.uuid4()).replace("-", "_")
        self.html_w = 1024
        self.html_h = 600 # will be adjusted as needed to maintain aspect ratio
        self.histogram_scale_w = 0
        self.histogram_scale_h = 0

        # Locale auto-guess. If locale hasn't been explictly specified via
        # commandline option, we will read the header and iterate the events
        # until we can guess the locale. Then we will reset the file pointer
        # to the start of the event list, reinitialize any text strings,
        # and clear the event list.
        global locale
        if debug:
            p("Locale initially set to " + locale)
        if locale == "auto":
            self.read_header()
            offset = self.r.tell()
            if debug:
                p("Will try to guess locale from event text.")
            last_turn = -1
            while locale == "auto":
                last_map = self.map_string()
                evt = self.read_event()
                if evt.turn != last_turn:
                    # p(last_map)
                    last_turn = evt.turn
                if ( evt.is_last_event() or (len(self.events) >= self.event_count-1) ):
                    break
            self.r.seek(offset)
            if locale == "auto":
                locale = "en"
                if debug:
                    p("Locale guess failed! Defaulting to English.")
            self.l_founded_comp = re.compile(self.l_founded_re.s(), re.U)
            self.difficulty = difficulty_strings[self.difficulty_level]
            ms = map_sizes[self.map_size_id]
            self.map_size = ms[0]
            self.victory_type = victory_types.get(self.victory_type_id, "unknown")
            self.events = []
    
    def get_enabled_victory_types(self):
        if len(self.victory_types) == 0:
            return "None"
        return ", ".join(map(lambda x:victory_types[x].s(), self.victory_types))

    def get_game_options(self):
        if len(self.game_options) == 0:
            return "None"
        return ", ".join(map(lambda x:game_options[x].s(), self.game_options))


    def set_background(self, map):
        self.background = map
        self.w = map.w
        self.h = map.h

    def read_header(self):
        """ Read the entire header before the first event """
        if self.leader_name is not None:
            return

        self.read_int() # always 5?
        self.read_int() # always 0?
        self.difficulty_level = self.read_int()
        self.difficulty = difficulty_strings[self.difficulty_level]

        # Civ info and map type follow                  # Examples:
        self.leader_name = self.read_string()           # "Oda Nobunaga"
        self.civ_name = self.read_string()              # "Japanese Empire"
        self.civ_name_short = self.read_string()        # "Japan"
        self.civ_name_possessive = self.read_string()   # "Japanese"
        self.map_script = self.read_string()            # "Assets\Maps\Pangea.lua"

        # Strip the path and .lua suffix from the map script to get the name
        self.map_name = re.split("[/\\\\]",self.map_script)[-1].rsplit(".",1)[0]

        # Next up might be the map size...
        self.map_size_id = self.read_int()
        ms = map_sizes[self.map_size_id]
        self.map_size = ms[0]
        if self.background is None:
            self.w = ms[1]
            self.h = ms[2]
  
        # Read remaining stuff I don't understand yet
        hd = []

        # All replay files that I have say 0,1,0 here
        hd.append(self.read_int())
        hd.append(self.read_int())
        hd.append(self.read_int())
        # Next one is either 0, 2 or 3 in my files
        hd.append(self.read_int())

        # Array containing numeric ids for advanced game options that were enabled
        self.game_options = self.read_ints()
        self.occ = option_occ in self.game_options
        self.noraze = option_noraze in self.game_options

        # Array containing numeric ids for victory types that were enabled
        self.victory_types = self.read_ints()

        # The victory type (-1 for a loss)
        self.victory_type_id = self.read_int()
        self.victory_type = victory_types.get(self.victory_type_id, "unknown")

        # How many events there are
        self.event_count = self.read_int()

        # MP: this does not match my replay files, mine seem to immediately go to the data here so
        # the end result is that some of the initial culture gets skipped.
        # All my files now have 0,1
        hd.append(self.read_int())
        hd.append(self.read_int())

        # I only have two different cases in my replay files for these
        # bytes: 1) a 2 and 4 more bytes, 2) a 0 and no more bytes
        hd.append(self.read_ints(esize=2))

        # there seems to be a -1 here
        hd.append(self.read_int())

        if debug:
            p("I think the content starts at offset", self.r.tell())

        self.header_data = hd

    def read_event(self):
        """ Read one event and return a Civ5ReplayEvent object """
        if self.fully_read:
            return None
        self.read_header()
        event = []
        event.append(self.read_int())
        is_last = False
        # MP: Changed the following to >= because of flexd replay 4cf2c522b878bc5e89000004
        # which somehow had one more event than expected in the list.
        if (len(self.events)>=self.event_count-1 and event[0] not in (1,2)) or (event[0] == 0):
            # Special rules for the end of the replay
            event.extend(self.read_ints(2))
            event.extend([0,0,0])
            is_last = True
        elif event[0] == -1:
            # I've only seen this in one replay file (note to self: Augustus Caesar_0332 AD-1912_0)
            self.read_int()
            event = [1,0,0,-1,-1,0]
        elif event[0] not in (0,1,2):
            print event, len(self.events), self.event_count
            # I've only seen this in one replay file (note to self: Gandhi_0500 AD-2050-_1)
            # MP: Added self.eof check because this was infinite looping on the flexd replay 4cf2c522b878bc5e89000004
            while ( (self.read_int() != -1) and (self.eof == False) ):
                pass
            return Civ5ReplayEvent([1,0,0,-1,-1,0], "")
        else:
            event.extend(self.read_ints(5))
        event_text = self.read_string()
        evt = Civ5ReplayEvent(event, event_text, is_last)
        self.events.append(evt)
        if evt.is_last_event():
            self.fully_read = True
            self.final_turn = evt.turn
            self.final_year = evt.text
            self.start_year = evt.start_year
            self.start_turn = evt.start_turn
            self.read_histogram()
        else:
            event_end = self.read_int()
            if event_end != -1:
                print evt, event_end
            assert(event_end == -1)
            # Guess locale based upon event text. There's probably a much shorter
            # and more efficient way to do this....
            global locale
            if locale == "auto":
                for k,v in self.l_founded_str.items():
                    if isinstance(v,unicode):
                        if v in evt.text:
                            locale = k
                            if debug:
                                p("Locale set to " + k + " based on city found event on turn " + str(evt.turn))
                            break
            if locale == "auto":
                for k,v in self.l_captured.items():
                    if isinstance(v,unicode):
                        if v in evt.text:
                            locale = k
                            if debug:
                                p("Locale set to " + k + " based on city capture event on turn " + str(evt.turn))
                            break
            if locale == "auto":
                for k,v in self.l_razed.items():
                    if isinstance(v,unicode):
                        if v in evt.text:
                            locale = k
                            if debug:
                                p("Locale set to " + k + " based on city razed event on turn " + str(evt.turn))
                            break
            if locale == "auto":
                for k,v in self.l_victory.items():
                    if isinstance(v,unicode):
                        if v in evt.text:
                            locale = k
                            if debug:
                                p("Locale set to " + k + " based on victory event on turn " + str(evt.turn))
                            break
            # reset captured data if this is a new turn
            if len(self.events)>1 and evt.turn != self.events[-2].turn:
                self.captured = {}
            # remember victory message
            if self.l_victory.s() in evt.text:
                self.victory_text = evt.text
            # remember city name
            if evt.event_type == 1:
                evt.city = 1
                if self.l_founded_comp is not None:
                    m = self.l_founded_comp.match(evt.text)
                    if m is not None:
                        city = m.group(1)
                        self.cities[(evt.x, evt.y)] = city
                        if evt.turn == 0 and evt.civ == 01:
                            self.citystates[(evt.x, evt.y)] = city
                        evt.city_name = city
                        evt.city = 1
                        # try to guess the civ from the first city it founds
                        if evt.civ != -1:
                            while len(self.civs) <= evt.civ:
                                self.civs.append(["Unknown Empire", "Unknown First City", "black", "white"])
                            if self.civs[evt.civ][0] == "Unknown Empire":
                                for c in civs:
                                    if c[1] == city:
                                        self.civs[evt.civ] = map(unicode,c)
            if (evt.x, evt.y) in self.cities:
                # we already know from earlier that this tile has a city
                evt.city = 1
                evt.city_name = self.cities[(evt.x, evt.y)]
            if self.l_razed.s() in evt.text:
                # the city on this tile is being razed
                if evt.city == 1:
                    self.razed.append((evt.x, evt.y))
            captured = self.l_captured.s()
            if captured in evt.text:
                # if it was being razed, it now no longer is
                if (evt.x, evt.y) in self.razed:
                    self.razed.remove((evt.x, evt.y))
                self.captured[(evt.x, evt.y)] = evt.civ
            if evt.city == 1 and evt.civ == -1:
                # if this tile has a city that is in the list of cities
                # that are being razed, remove the city flag and mark
                # the event as aazing that tile
                if (evt.x, evt.y) in self.razed:
                    self.razed.remove((evt.x, evt.y))
                    del self.cities[(evt.x, evt.y)]
                    evt.city = -1
                    evt.city_name = ""
                    self.domain_raze(evt.turn, evt.x, evt.y)
                # if this city has its ownership reset and was just
                # captured during the same turn by an empire (not a
                # city state), then this is either a city that was
                # liberated, or a city that was auto-razed in a OCC
                # game (sometimes the captured message seems to be
                # missing?)
                if self.occ and self.captured.get((evt.x, evt.y), -1) == 0:
                    if (evt.x, evt.y) in self.cities:
                        del self.cities[(evt.x, evt.y)]
                    evt.city = -1
                    evt.city_name = ""
                    self.domain_raze(evt.turn, evt.x, evt.y)

        evt.update_map(self.map)
        evt.update_domain(self.domain)
        if evt.x >= self.w:
            self.w = evt.x+1
        if evt.y >= self.h:
            self.h = evt.y+1
        return evt
    
    def read_histogram(self):
        """ Read the histogram data from the replay"""
        if not self.histogram is None:
            return
        replay.read_int()  # 0
        replay.read_int()  # time?
        civs = replay.read_int()
        histogram = []
        x = 0
        self.histogram_w = 0
        self.histogram_h = 0
        for civ in range(civs):
            a = replay.read_int() # ?
            b = replay.read_int() # ?
            turns = replay.read_int() # number of 4-int data points for this civ
            if turns > self.histogram_w:
                self.histogram_w = turns
            for turn in range(turns):
                while turn >= len(histogram):
                    histogram.append([0] * civs)
                a = replay.read_int() # score?
                b = replay.read_int() # ?
                c = replay.read_int() # ?
                d = replay.read_int() # ?
                histogram[turn][civ] = a
        for line in histogram:
            score_sum = reduce(lambda a,b:a+b, line)
            if score_sum > self.histogram_h:
                self.histogram_h = score_sum
        self.histogram = histogram

    def csv(self):
        """ Return the score histogram in csv format """
        self.read_full()
        hist_csv = ""
        for l in self.histogram:
            hist_csv += ",".join(map(str,l)) + "\n"
        return hist_csv

    def read_full(self):
        """ Make sure to read everything we understand """
        if not self.fully_read:
            self.read_header()
            while True:
                evt = self.read_event()
                if evt.is_last_event():
                    break
        self.read_histogram()
    
    def domain_raze(self, turn, x, y):
        """ Mark a city as razed on turn X """
        if x < 0 or y < 0:
            return
        di = self.domain_info(turn, x, y)
        while len(self.domain) <= y:
            self.domain.append([])
        ln = self.domain[y]
        while len(ln) <= x:
            ln.append({})
        d = ln[x]
        d[turn] = [ turn, di[1], -1, "" ]

    def domain_info(self, turn, x, y):
        """ Returns tile ownership on turn X """
        if y < 0 or x < 0:
            return None
        if y >= len(self.domain):
            return None
        ln = self.domain[y]
        if x >= len(ln):
            return None
        d = ln[x]
        data = [None]*4
        for a in sorted(d.keys()):
            if a <= turn:
                data[0] = d[a][0]
                data[1] = d[a][1]
                if d[a][2] != 0: 
                    data[2] = d[a][2]
                if d[a][3] is not None:
                    data[3] = d[a][3]
        return data

    def neighbours(self, x, y):
        xoff = y % 2
        return [
            ( x+xoff, y-1 ),
            ( x+1, y ),
            ( x+xoff, y+1 ),
            ( x-1+xoff, y+1 ),
            ( x-1, y ),
            ( x-1+xoff, y-1 ),
        ]

    def domain_region(self, turn, x, y):
        """ Return all the tiles part of a contiguous region that contains x,y as of turn X """
        comp = self.domain_info(turn, x, y)
        queue = [ (x,y,comp) ]
        region = []
        while len(queue)>0:
            tile = queue.pop(0)
            if tile[2] is None:
                continue
            if tile[2] == {}:
                continue
            if tile in region:
                continue
            if tile[2][1] != comp[1]:
                continue
            region.append(tile)
            for nx, ny in self.neighbours(tile[0], tile[1]):
                queue.append((nx, ny, self.domain_info(turn, nx, ny)))    
        return region

    def domain_region_intersect(self, a, b):
        """ Return the intersection of two regions, assuming the second region has the more recent data """ 
        ret = []
        for ra in a:
            for rb in b:
                if rb[0] == ra[0] and rb[1] == ra[1]:
                    ret.append(rb)
        return ret

    def domain_region_has_city(self, region):
        """ Determine whether a region as returned by domain_region() contains a city """
        for i in region:
            if i[2][2] == 1:
                return True
        return False

    def quotehtml(self, txt):
        return "".join(html_escape.get(x,x) for x in txt)

    def html(self):
        """ Returns an HTML rendering of an animated map. Only the HTML necessary to display the information is returned, no full HTML skeleton is created to facilitate embedding the map in web pages. """
        # make sure we know all there is to know about this replay
        self.read_full()

        # calculate sizes
        self.tile_size = (self.html_w*1.0 / (self.w+1.5))
        self.html_h = 2.0/3.0*self.tile_size * (self.h + 1.5)
        
        # calculate histogram sizes
        self.histogram_scale_w = self.html_w*1.0/self.histogram_w
        self.histogram_scale_h = self.html_h*1.0/self.histogram_h

        # escape some text for good measure
        for v in ("leader_name", "civ_name", "map_name", "final_year", "victory_text"):
            setattr(self, v, self.quotehtml(getattr(self, v)))

        # create the HTML event list for the log
        h = "<table>"
        for evt in self.events:
            if evt.text != "":
                type = "event"
                h += """
                    <tr>
                        <td class="%(id)s_base_turn %(id)s_%(type)s_turn">%(l_Turn)s %(turn)s</td>
                        <td class="%(id)s_base_text %(id)s_%(type)s_text">%(text)s</td>
                    </tr>""" % {
                        "id":       self.id,
                        "type":     type,
                        "turn":     evt.turn,
                        "text":     self.quotehtml(evt.text),
                        "l_Turn":   self.l_Turn,
                    }
        h += "</table>"
        self.html_event_list = h

        # make game options available to html
        h = ""
        if len(self.game_options) > 0:
            h = self.get_game_options()
        if len(self.victory_types) != len(victory_types)-1:
            dvt = []
            for vt in victory_types:
                if vt < 0:
                    continue
                if not vt in self.victory_types:
                    dvt.append(victory_types[vt].s())
            if len(h) > 0:
                h += " | "
            h += "/".join(map(lambda x: '<span class="%s_disabled_option">%s</span>' % (self.id, x,), dvt))
        if len(h) > 0:
            h = " " + h + " |"
        self.options_pipe = h

        # make civs array available to javascript
        j = u"[\n"
        for c in self.civs:
            j += "    ["
            for v in c:
                j += '"%s",' % (v,)
            j += "],\n"
        j += "]"
        self.javascript_civs = j

        # create the javascript event list for drawing
        last_event = None
        j = "[\n"
        for evt in self.events:
            if evt.x > -1 and evt.y > -1:
                if evt.civ == -1:
                    # -1 is either a tile flipping to a city state,
                    # or a tile losing its owner (e.g. due to razing)
                    # for now, razed tiles are shown using the same
                    # colours as city state owned tiles, but due to
                    # the above magic, at least the city indicator
                    # circle thingy will disappear
                    fg = citystate_color[0]
                    bg = citystate_color[1]
                    if evt.turn > 0:
                        # if the tile is set to -1 when it is already -1,
                        # a good guess is that a city state razed the tile
                        d = self.domain_info(evt.turn-1, evt.x, evt.y)
                        if d is not None and d[1] is not None:
                            if d[1] == -1:
                                fg = "transparent"
                                bg = "transparent"
                            # if the tile is set to -1, but at the end of the
                            # turn belongs to a contiguous -1 region that has
                            # no city in it, it must have been razed
                            r = self.domain_region(evt.turn, evt.x, evt.y)
                            if not self.domain_region_has_city(r):
                                fg = "transparent"
                                bg = "transparent"
                            else:
                                # if the tile is set to -1 and had an owner before, 
                                # determine the intersection between the region it 
                                # belongs to at the end of this turn and the region 
                                # it belonged to at the end of the previous turn, 
                                # and if this intersection does not contain a city, 
                                # conclude that the tile must have been razed
                                r_before = self.domain_region(evt.turn-1, evt.x, evt.y)
                                r_i = self.domain_region_intersect(r_before, r)
                                if not self.domain_region_has_city(r_i):
                                    fg = "transparent"
                                    bg = "transparent"
                elif evt.civ >= 0:
                    # a tile is being flipped to a new owner
                    #MP debug
                    #p("city flip event for civ " + str(evt.civ))
                    fg = self.civs[evt.civ][2]
                    bg = self.civs[evt.civ][3]
                else:
                    bg = "white"
                    fg = "black"
                cn = evt.city_name
                if cn is None:
                    cn = ""
                e = ( evt.turn, evt.x, self.h-evt.y-1, bg, fg, self.quotehtml(evt.text), evt.city, self.quotehtml(cn) )
                j += '    [ %d, %d, %d, "%s", "%s", "%s", %d, "%s" ],\n' % e
                last_event = e
            elif evt.text != "":
                e = ( evt.turn, -1, -1, "", "", self.quotehtml(evt.text), 0, "" )
                j += '    [ %d, %d, %d, "%s", "%s", "%s", %d, "%s" ],\n' % e
                last_event = e
        j += "]"
        self.javascript_event_list = j

        # map event list index to turn number for javascript
        j = "["
        turn = 0
        ec = 0
        for evt in self.events:
            while evt.turn >= turn:
                j += "%d, " % (ec,)
                turn += 1
            ec += 1
        j += "]"
        self.javascript_turn_to_event = j

        # create the javascript histogram data
        j = "[\n"
        for line in self.histogram:
            j += "    %s,\n" % (str(line),) 
        j += "]"
        self.javascript_histogram_score = j

        # create the javascript background map data
        j = "[\n"
        if self.background is not None:
            for line in self.background.map:
                j += "    ["
                for tile in line:
                    hf = tile[3]
                    if tile[2] == "FEATURE_ICE":
                        hf = -1;
                    rf = tile[4]
                    j += '["%s",%d,%d],' % (map_colors.get(tile[0],""),hf,rf)
                j += "],\n"
        j += "]"
        self.javascript_background = j
        
        # assemble the HTML
        ret = html_header % self.__dict__
        ret += html_javascript % self.__dict__
        ret += html_skeleton % self.__dict__
        return ret

    def leader_info(self):
        """ Return a human-readable short description including the leader name, civilization name and map name """
        self.read_header()    
        return L("%s of the %s (%s, %s, %s)", fr="%s de l'%s (%s, %s, %s)") % (self.leader_name, self.civ_name, self.difficulty, self.map_size, self.map_name)

    def map_string(self):
        """ Make a half-assed attempt at rendering the map as of the last event read as a human-readable string """
        ret = ""
        indent = len(self.map)%2 == 0
        for line in reversed(self.map):
            if indent:
                ret += " "
            for field in line:
                t = "  "
                if field > 0:
                    t = "%d%d" % (field, field)
                elif field == -2:
                    t = "##"
                elif field == -1:
                    t = "**"
                ret += t
            ret += "\n"
            indent = not indent
        return ret

# If run as a script, read the first file given on the command line
# Some options exist, run with -h to see them
if __name__ == "__main__":
    # set up some command line options
    op = optparse.OptionParser()
    op.add_option("-d", "--debug", action="store_true",
        help="Run in debug mode")
    op.add_option("-q", "--quiet", action="store_true",
        help="Less output")
    op.add_option("-l", "--locale",
        help="Set locale to LOCALE (e.g. en, fr, ...)", metavar="LOCALE")
    op.add_option("-m", "--map", 
        help="Read background map from MAPFILE", metavar="MAPFILE")
    op.add_option("-w", "--width", 
        help="Make the HTML canvas WIDTH pixels wide", metavar="WIDTH")
    op.add_option("-H", "--html",
        help="Write HTML output to FILE", metavar="FILE")
    op.add_option("-C", "--csv",
        help="Write CSV output to FILE", metavar="FILE")
    (options, args) = op.parse_args()

    if len(args) == 0 and options.map is None:
        p("You need to tell me which replay file I should examine.")
        sys.exit(1)

    if options.locale:
        locale = options.locale

    if options.debug:
        debug = True

    replay = None
    if len(args) > 0:
        p("Replaying: %s" % (args[0],))
        if not options.quiet:
            p("-" * 78 + "\n")
        replay = Civ5Replay(args[0])
        p("Leader:", replay.leader_info())
        p("Victory type: %s" % (replay.victory_type))
        p("Game options: %s; enabled victory types: %s" % (replay.get_game_options(), replay.get_enabled_victory_types()))
        if args[0].endswith(".Civ5Replay"):
            base = args[0].rsplit(".", 1)[0]
            if options.html is None:
                if os.path.exists(base + ".html"):
                    p(base+".html", "already exists, NOT overwriting!")
                else:
                    options.html = base + ".html"
            if options.map is None:
                if os.path.exists(base + ".Civ5Map"):
                    options.map = base + ".Civ5Map"

    if options.width:
        replay.html_w = int(options.width);

    if options.map:
        the_map = Civ5Map(options.map)
        p("Map:", the_map.map_info(), options.map)
        if replay:
            replay.set_background(the_map)

    if len(args) == 0:
        p("No replay file was given.")
        sys.exit(0)

    # Read all events and print them
    last_turn = -1
    while True:
        last_map = replay.map_string()
        evt = replay.read_event()
        if evt.turn != last_turn:
            # p(last_map)
            last_turn = evt.turn
        if not options.quiet:
            if options.debug:
                p(unicode(evt) + " [%d,%d]" % (evt.x, evt.y))
            else:  
                p(evt)
        if evt.is_last_event():
            if options.quiet:
                p("Game ends after %d turns in %s" % (evt.turn, evt.text))
            break

    # Export HTML
    if options.html:
        p("Writing HTML to %s" % (options.html,))
        html = codecs.open(options.html, "w", "utf-8")
        html.write(replay.html())
        html.close()
    
    # Export histogram as CSV if requested
    if options.csv:
        p("Writing CVS to %s" % (options.csv,))
        csv = codecs.open(options.csv, "w", "utf-8")
        csv.write(replay.csv())
        csv.close()

