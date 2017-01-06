"""
Flaming Goose Bot:
    A Discord bot written by Ethan Wilton.
    Maintains user profiles with reputation, exp and levels.
    Also performs other miscelaneous functions. Use ">>help" or ">>h" in Discord for more info.
    For full functionality, ensure the bot has permission to manage messages and reactions.
"""

from os.path import exists as path_exists
from re import search as regex_search
from json import dump as json_dump
from json import load as json_load
from re import findall
from random import randint
import discord

def get_user_from_name(server, name, discriminator=None):
    '''
    Returns the first user id in server matching name.
    Also uses discriminator if provided.
    Returns false if no matches are found.
    '''
    if discriminator is not None:
        for user in CLIENTDATA[server]['users']:
            if CLIENTDATA[server]['users'][user]['name'] == name:
                if CLIENTDATA[server]['users'][user]['discriminator'] == discriminator:
                    return user
    else:
        for user in CLIENTDATA[server]['users']:
            if CLIENTDATA[server]['users'][user]['name'] == name:
                return user

def filter_flags(arguments, flags):
    '''
    checks a list of arguments against a list of flags
    Returns a dictonary with a key 'flags' containing a list of flags found
    and a key 'argscontaining a list of arguments that are not flags
    '''
    results = {'args': [], 'flags': []}
    for arg in arguments:
        if arg in flags:
            if arg not in results['flags']:
                results['flags'].append(arg)
            arguments.remove(arg)

    results['args'] = arguments
    return results

CLIENTDATA = {}
HELPMESSAGES = {
    'help': 'Displays the Goosebot help dialogue\n'
            + '    Usage: ">>help"\n',
    'roll': 'simulates rolling a die with y sides x times\n'
            + '    Usage: ">>roll xdy"\n'
            + '    example: ">>roll 5d6" -> "[1,3,6,2,3]"',
}

CLIENT = discord.Client()

@CLIENT.event
async def on_ready():
    'initialization events and stdout readouts for when CLIENT is connected'
    global CLIENTDATA

    #either load data from .json or create default data and write to .json
    if path_exists('./clientdata.json'):
        CLIENTDATA = json_load(open('./clientdata.json', 'r'))

        #now check for inconsistencies between clientdata.json and CLIENT attributes:
        for server in CLIENT.servers:
            #first, check for new users
            for user in server.users:
                if user.id not in CLIENTDATA[server.id]['users']:
                    CLIENTDATA[server.id]['users'][user.id] = {
                        'name': user.name,
                        'discriminator': user.discriminator,
                        'pronouns': [],
                        'keywords': [],
                        'posts': 0
                    }
                #check to make sure usernames havent changed
                elif user.name != CLIENTDATA[server.id]['users'][user.id]['name']:
                    CLIENTDATA[server.id]['users'][user.id]['name'] = user.name
            
            #check for new channels
            for channel in CLIENT.channels:
                if channel.id not in CLIENTDATA[server.id]['banned words']:
                    CLIENTDATA[server.id]['banned words'][channel.id] = []

    else:
        print('Client data not found. Generating new profiles for users...')
        CLIENTDATA = {server.id: {
            'name': server.name,
            'banned words': {channel.id: [] for channel in server},
            'custom responses': {},
            'hidden channels': {},
            'users': {
                member.id: {
                    'name': member.name,
                    'discriminator': member.discriminator,
                    'pronouns': [],
                    'keywords': [],
                    'posts': 0,
                    #'rep': 0
                } for member in server.members if member.id != CLIENT.user.id
            }
        } for server in CLIENT.servers}
        json_dump(CLIENTDATA, open('./clientdata.json', 'w+'))
        print('done')

    #make sure all the command custom emojis are present
    #FIXME: take care of getting correct byte object for images
    '''for server in CLIENT.servers:
        if '+rep' not in server.emojis:
            await CLIENT.create_custom_emoji(server,
                                             name='+rep',
                                             image=open('./icons/+rep.png', mode='rb').read())

        if '-rep' not in server.emojis:
            await CLIENT.create_custom_emoji(server,
                                             name='-rep',
                                             image=open('./icons/-rep.png', mode='rb').read())'''


    print('connected to discord as ' + CLIENT.user.name + ' #' + CLIENT.user.discriminator)
    print('connected servers:')
    for server in CLIENT.servers:
        print('    ' + server.name + ' [id ' + server.id + ']')


@CLIENT.event
async def on_message(message):
    'all the bot commands and checks performed when a message is sent'
    global CLIENTDATA
    author = message.author
    channel = message.channel
    server = message.server
    content = message.content

    if author == CLIENT.user:
        return
    else:
        CLIENTDATA[server.id]['users'][author.id]['posts'] += 1

    #check message for banned words
    for word in CLIENTDATA[server.id]['banned words'][channel.id]:
        if findall(r'\b' + word + r'\b', content) != []:
            await CLIENT.delete_message(message)
            await CLIENT.send_message(channel,
                                      author.mention + ' said a bad word. For shame!\n'
                                      + 'https://youtu.be/wqfCi1qAGAo')
            CLIENTDATA[server.id]['users'][author.id]['rep'] -= 1
            return

    #check for user keywords
    msg = ''
    for person in server.members:
        for keyword in CLIENTDATA[server.id]['users'][person.id]['keywords']:
            if content.count(keyword) != 0:
                msg += person.mention + ', '

    await CLIENT.send_message(channel, msg)


    if content.startswith('>>'):
        content = content.lstrip('>>')
        command = findall(r'\S+', content)[0]
        args = findall(r'\S+', content)[1:]

        #help dialogue
        if (command == 'help') or (command == 'h'):
            msg = '```Goosebot help dialogue:\n\n'
            for key in HELPMESSAGES:
                msg += key + '-\n'
                msg += HELPMESSAGES[key] + '\n\n'

            msg += '```'
            await CLIENT.send_message(channel, msg)

        #smple diceroller
        elif command == ('roll'):
            if len(args) != 1 or regex_search(r'\d+d\d+', content) is None:
                await CLIENT.send_message(channel, '```Error: invalid syntax for ">>roll"\n'
                                          + HELPMESSAGES['roll'] + '```')
            else:
                rolls = regex_search(r'\d+(?=d)', args).group(0)
                sides = regex_search(r'(?<=d)\d+', args).group(0)
                results = []
                for number in range(0, int(rolls)):
                    results.append(randint(1, int(sides)))

                await CLIENT.send_message(channel, '`' + str(results) + '`')

        #display rep and description for a certain user
        elif command == ('info'):
            if len(args) == 0:
                await CLIENT.send_message(channel, 'Error: no arguments given')
            else:
                del args[0]
                users = CLIENTDATA[server.id]['users']
                for arg in args:
                    user = get_user_from_name(server.id, arg)
                    pronoun_string = ''
                    for pronoun in users[user]['pronouns']:
                        pronoun_string += pronoun
                        if users[user]['pronouns'] != users[user]['pronouns'][-1]:
                            pronoun_string += ', '

                    await CLIENT.send_message(channel,
                                              '```User ' + users[user]['name'] + ':\n'
                                              #+ '    rep: ' + str(users[user]['rep']) + '\n'
                                              + '    posts: ' + users[user]['posts']
                                              + '    preffered pronouns: ' + pronoun_string
                                              + '```')

        elif command == ('setpronouns'):
            valid_pronouns = ['they', 'they/them', 'he', 'he/him', 'she', 'she/her']
            for arg in args:
                if arg in valid_pronouns:
                    CLIENTDATA[server.id]['users'][author.id]['pronouns'].append(arg)
                else:
                    await CLIENT.send_message(
                        channel,
                        '`Error: ' + arg + ' Is not considered a valid pronoun.'
                        + 'Please contact '
                        + [role for role in server.roles if role.name == 'Botmaster'][0].mention()
                        + ' if you have any questions'
                        + ' or you feel another valid pronoun should be added.'
                    )

        elif command == ('add-custom-response'):
            if len(args) == 2:
                CLIENTDATA[server.id]['custom responses'][args[0]] = args[1]
                await CLIENT.send_message(channel, 'Custom response added')
            elif len(args) > 2:
                await CLIENT.send_message(channel, '`Error: too many arguments`')
            elif len(args) < 2:
                await CLIENT.send_message(channel, '`Error: too few arguments`')

        elif command == ('add-banned-word'):
            filtered_args = filter_flags(args, ['-p', '--phrase', '-g', '--global'])
            args = filtered_args['args']
            flags = filtered_args['flags']
            if len(args) == 1:
                if '-g' in flags or '--global' in flags:
                    for channel_ in CLIENTDATA[server.id]['banned words']:
                        CLIENTDATA[server.id]['banned words'][channel_].append(args[0])

                    await CLIENT.send_message(channel, 'Banned word added to all channels')
                else:
                    CLIENTDATA[server.id]['banned words'][channel.id].append(args[0])
                    await CLIENT.send_message(channel, 'Banned word added to this channel only')

            elif len(args) > 1:
                if '-g' in flags or '--global' in flags:
                    if '-p' in flags or '--phrase' in flags:
                        for word in args[:len(args)-1]:
                            word += ' '

                        for channel_ in CLIENTDATA[server.id]['banned words']:
                            CLIENTDATA[server.id]['banned words'][channel_].append(''.join(args))

                        await CLIENT.send_message(channel, 'Banned phrase added to all channels')
                    else:
                        for channel_ in CLIENTDATA[server.id]['banned words']:
                            CLIENTDATA[server.id]['banned words'][channel_] += args

                        await CLIENT.send_message(channel, 'Banned words added to all channels')
                else:
                    if '-p' in flags or '--phrase' in flags:
                        for word in args[:len(args)-1]:
                            word += ' '

                        CLIENTDATA[server.id]['banned words'][message.channel].append(''.join(args))
                        await CLIENT.send_message(channel,
                                                  'Banned phrase added to this channel only')
                    else:
                        CLIENTDATA[server.id]['banned words'][message.channel] += args
                        await CLIENT.send_message(channel,
                                                  'Banned words added to this channel only')
            else:
                await CLIENT.send_message(channel, '`Error: too few arguments`')

        elif command == ('remove-banned-word'):
            if len(args) == 1:
                CLIENTDATA[server.id]['banned words'][channel.id].remove(args[0])
                await CLIENT.send_message(channel, 'Banned word removed from this channel')
            elif len(args) < 1:
                for arg in args:
                    arg += ' '

                CLIENTDATA[server.id]['banned words'][channel.id].remove(''.join(args))
                await CLIENT.send_message(channel, 'Banned phrase removed from this channel')
            else:
                await CLIENT.send_message(channel, '`Error: too few arguments`')

        #elif command == ( 'joinchannel '):

        #allows non-admins to make new channels. commented until permissions are figured out.
        '''elif command == ( 'makechannel '):
            channel_name = content.lstrip('>>makechannel ')
            everyone = discord.PermissionOverwrite(read_messages=False)
            creator = discord.PermissionOverwrite(read_messages=True)
            new_role = await CLIENT.create_role(
                message.server,
                name='can access ' + channel_name,
                hoist=False,
                mentionable=False,
            )
            new_channel = await CLIENT.create_channel(server, channel_name,
                                                      (server.default_role, everyone),
                                                      (message.author, creator))
            await CLIENT.send_message(channel,
                                      'New channel ' + new_channel.mention
                                      + ' created by ' + author.mention)

            CLIENTDATA[CLIENT.server]['hidden channels'][new_channel.id] = []'''

#commented out until adding emojis is figured out
'''
@CLIENT.event
async def on_reaction_add(reaction, user):
    'manages events triggered by reactions (aka ones where using a full command would be bodgy)'
    global CLIENTDATA
    message = reaction.message

    if reaction.emoji == '+rep':
        CLIENTDATA[server.id]['users'][author.id]['rep'] += 1

    elif reaction.emoji == '-rep':
        CLIENTDATA[server.id]['users'][author.id]['rep'] -= 1

@CLIENT.event
async def on_reaction_remove(reaction, user):
    global CLIENTDATA
    message = reaction.message

    if reaction.emoji == '+rep':
        CLIENTDATA[message.esrver.id]['users'][author.id]['rep'] -= 1

    elif reaction.emoji == '-rep':
        CLIENTDATA[message.esrver.id]['users'][author.id]['rep'] += 1
'''

@CLIENT.event
async def on_channel_create(channel):
    'initalize list of banned words for new servers'
    global CLIENTDATA
    CLIENTDATA[channel.server]['banned words'][channel.id] = []

@CLIENT.event
async def on_channel_delete(channel):
    'clean up list of banned words for deleted servers'
    global CLIENTDATA
    del CLIENTDATA[channel.server]['banned words'][channel.id]

@CLIENT.event
async def on_member_join(member):
    'create a user profile someone joins a server'
    global CLIENTDATA
    CLIENTDATA[member.server.id]['users'][member.id] = {
        'name': member.name,
        'discriminator': member.discriminator,
        'pronouns': [],
        'keywords': [],
        'posts': 0
    }
    await CLIENT.send_message(member.server.default_channel(),
                              member.mention() + 'has joined the server!')

@CLIENT.event
async def on_member_update(before, after):
    'keep track of username changes'
    global CLIENTDATA
    if before.name != after.name:
        CLIENTDATA[after.server.id]['users'][after.id]['name'] = after.name

@CLIENT.event
async def on_member_remove(member):
    'clean up CLIENTDATA when people leave a server'
    global CLIENTDATA
    del CLIENTDATA[member.server.id]['users'][member.id]

CLIENT.run('MjY1NjQyODk2ODgyMDA4MDc0.C0yGwg.wSKmoU3MntI8Mo_X9VFcH-G4I-U')
json_dump(CLIENTDATA, open('./clientdata.json', 'w'), indent=4)
