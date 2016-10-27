import re

from commands import CommandReturn
from commands.say import SayFilter
from core import PLATFORM
from engines.server import engine_server
from events import Event
from listeners import OnClientActive
from memory import Convention, DataType, get_object_pointer, make_object
from memory.hooks import PreHook
from _messages import ProtobufMessage
from messages import get_message_index
from players.entity import Player

from .info import info
from .paths import ADPURGE_DATA_PATH
from .tlds import tlds


CENSORED_NAME = "Advertiser #{userid:04}"
REPLACE_DOMAIN_RES_PATH = ADPURGE_DATA_PATH / "replace-domain.res"
REPLACE_IP_RES_PATH = ADPURGE_DATA_PATH / "replace-ip.res"
DOMAIN_AD_REGEX = re.compile(r"\w+\.({tlds})".format(tlds='|'.join(tlds)))
IP_AD_REGEX = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
TEXTMSG_INDEX = get_message_index('TextMsg')
SAYTEXT2_INDEX = get_message_index('SayText2')
with open('regex.txt', 'w') as f:
    f.write(r"\w+\.({tlds})".format(tlds='|'.join(tlds)))

if PLATFORM == "windows":
    SEND_USER_MESSAGE_INDEX = 45
else:
    SEND_USER_MESSAGE_INDEX = 45


send_user_message = get_object_pointer(engine_server).make_virtual_function(
    SEND_USER_MESSAGE_INDEX,
    Convention.THISCALL,
    [DataType.POINTER, DataType.POINTER, DataType.INT, DataType.POINTER],
    DataType.VOID
)


def get_replacements(path):
    replacements = {}
    with open(path, 'rb') as f:
        for mapping in f.read().decode('utf-8').split('\n'):
            replace_what, replace_to = mapping.split(':')
            replacements[replace_what] = replace_to

    return replacements

replace_domains = get_replacements(REPLACE_DOMAIN_RES_PATH)
replace_ips = get_replacements(REPLACE_IP_RES_PATH)


def filter_text(text):
    text_domain = text_ip = text.lower()
    for replace_what, replace_to in replace_domains.items():
        text_domain = text_domain.replace(replace_what, replace_to)

    for replace_what, replace_to in replace_ips.items():
        text_ip = text_ip.replace(replace_what, replace_to)

    text_domain_re = DOMAIN_AD_REGEX.sub("", text_domain)
    text_ip_re = IP_AD_REGEX.sub("", text_ip)

    if text_domain_re == text_domain and text_ip_re == text_ip:
        return None

    text_domain_re = IP_AD_REGEX.sub("", text_domain_re)
    return text_domain_re


name_change = False


@Event('player_changename')
def on_player_changename(game_event):
    global name_change
    if name_change:
        return

    player = Player.from_userid(game_event['userid'])
    new_name = filter_text(game_event['newname'])
    if new_name is None:
        return

    name_change = True
    player.name = CENSORED_NAME.format(userid=player.userid)
    name_change = False


@SayFilter
def say_filter(command, index, team_only):
    new_text = filter_text(command.command_string)
    if new_text is None:
        return

    return CommandReturn.BLOCK


@OnClientActive
def listener_on_client_active(index):
    player = Player(index)
    new_name = filter_text(player.name)
    if new_name is None:
        return

    global name_change
    name_change = True
    player.name = CENSORED_NAME.format(userid=player.userid)
    name_change = False


@PreHook(send_user_message)
def pre_send_user_message(args):
    if args[2] not in (TEXTMSG_INDEX, SAYTEXT2_INDEX):
        return

    buffer = make_object(ProtobufMessage, args[3])

    # TextMsg: player connect messages
    if args[2] == TEXTMSG_INDEX:
        msg_name = buffer.get_repeated_string('params', 0)
        if msg_name == "#Game_connected":
            new_name = filter_text(buffer.get_repeated_string('params', 1))
            if new_name is not None:
                buffer.set_repeated_string('params', 1, "<censored>")

        return

    # SayText2: player changename messages
    if args[2] == SAYTEXT2_INDEX:
        msg_name = buffer.get_string('msg_name')

        if msg_name == "#Cstrike_Name_Change":
            if name_change:
                return

            # Old name
            new_name = filter_text(buffer.get_repeated_string('params', 0))
            if new_name is not None:
                buffer.set_repeated_string('params', 0, "<censored>")

            # New name
            new_name = filter_text(buffer.get_repeated_string('params', 1))
            if new_name is not None:
                buffer.set_repeated_string('params', 1, "<censored>")

        return

    # TODO: player disconnect messages
