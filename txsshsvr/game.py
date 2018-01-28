
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import collections
import itertools
import random
import sys
import textwrap
import six
from six.moves import (
    zip,
)
from twisted.python import log
from txsshsvr import graphics_chars as gchars
from txsshsvr import (
    session,
    users,
)
from txsshsvr.werewolf import WerewolfGame
from twisted.conch.insults.text import (
    attributes as A,
    assembleFormattedText,
)


class HandledWerewolfGame(WerewolfGame):
    PHASE_TWILIGHT = 0
    PHASE_WEREWOLVES = 10
    PHASE_MINION = 20
    PHASE_SEER = 30
    PHASE_ROBBER = 40
    PHASE_TROUBLEMAKER = 50
    PHASE_INSOMNIAC = 60
    PHASE_DAYBREAK = 70
    PHASE_ENDGAME = 80

    phase = None
    session_id = None
    wait_list = None
    power_activated = False
    seer_viewed_table_cards = None
    seer_viewed_player_card = None

    # --------------
    # Event handlers
    # --------------

    def handle_cards_dealt(self):
        log.msg("Cards have been dealt.")
        self.phase = self.PHASE_TWILIGHT
        self.set_wait_list()
        self.notify_players()

    def handle_werewolf_phase(self):
        log.msg("Entered the werewolf phase.")
        self.phase = self.PHASE_WEREWOLVES
        self.set_wait_list()
        self.notify_players()

    def handle_minion_phase(self):
        log.msg("Entered the minion phase.")
        self.phase = self.PHASE_MINION
        self.set_wait_list()
        self.notify_players()
    
    def handle_seer_phase(self):
        log.msg("Entered the seer phase.")
        self.phase = self.PHASE_SEER
        self.power_activated = False
        self.set_wait_list()
        self.notify_players()
    
    def handle_robber_phase(self):
        log.msg("Entered the robber phase.")
        self.phase = self.PHASE_ROBBER
        self.power_activated = False
        self.set_wait_list()
        self.notify_players()
    
    def handle_troublemaker_phase(self):
        log.msg("Entered the troublemaker phase.")
        self.phase = self.PHASE_TROUBLEMAKER
        self.power_activated = False
        self.set_wait_list()
        self.notify_players()
    
    def handle_insomniac_phase(self):
        log.msg("Entered the insomniac phase.")
        self.phase = self.PHASE_INSOMNIAC
        self.set_wait_list()
        self.notify_players()
    
    def handle_daybreak(self):
        log.msg("Entered daybreak phase.")
        self.phase = self.PHASE_DAYBREAK
        self.set_wait_list()
        self.notify_players()
    
    def handle_endgame(self):
        log.msg("Entered the endgame phase.")
        self.phase = self.PHASE_ENDGAME
        self.set_wait_list()
        self.notify_players()

    # ---------
    # Signaling
    # ---------

    def notify_players(self):
        """
        Notify all connected players that a change in game state has occured
        and they should update their UIs.
        """
        session_entry = session.get_entry(self.session_id)
        members = session_entry.members
        for player in members:
            user_entry = users.get_user_entry(player)
            app_protocol = user_entry.app_protocol
            app_protocol.reactor.callLater(0, app_protocol.handle_next_phase)

    def set_wait_list(self):
        """
        Wait until all players have signaled it is OK to advance.
        """
        session_entry = session.get_entry(self.session_id)
        members = session_entry.members
        self.wait_list = set(members)

    def signal_advance(self, player):
        """
        A player has indicated it is OK to advance to the next phase.
        """
        wait_list = self.wait_list
        wait_list.discard(player)
        if len(wait_list) == 0:
            self.advance_phase()
            
    
class GameProtocol(object):
    game = None
    user_id = None


class SSHGameProtocol(GameProtocol):
    reactor = None
    terminal = None
    term_size = (80, 24)
    parent = None
    commands = None
    game = None
    player_cards = None
    cards = None
    _ready_to_advance = False

    @classmethod
    def make_protocol(klass, **kwds):
        instance = klass()
        for k, v in kwds.items():
            setattr(instance, k, v)
        instance.commands = {}
        entry = users.get_user_entry(instance.user_id)
        session_entry = session.get_entry(entry.joined_id)
        players = session_entry.members
        if session_entry.game is None:
            game = HandledWerewolfGame()
            session_entry.game = game
            game.session_id = session_entry.session_id
            game.add_players(players)
            werewolf_count = 2
            wg = WerewolfGame
            other_roles = set([
                wg.CARD_SEER,
                wg.CARD_ROBBER,
                wg.CARD_TROUBLEMAKER,
                wg.CARD_MINION,
                wg.CARD_INSOMNIAC,
                wg.CARD_HUNTER,
                wg.CARD_TANNER,
            ])
            instance.reactor.callLater(
                0, game.deal_cards, werewolf_count, other_roles)
        instance.game = session_entry.game
        return instance

    def handle_input(self, key_id, modifier):
        """
        Handle user input.
        """ 
        func = self.commands.get(key_id)
        if func is None:
            func = self.commands.get('*', None)
            if func is None:
                return
        func()
        self.update_display() 

    def update_display(self):
        """
        Update the display.
        """
        terminal = self.terminal
        terminal.reset()
        tw, th = self.term_size
        self._draw_border()
        self._draw_player_area()
        self._draw_game_info_area()
        self._draw_phase_area()
        terminal.cursorPosition(0, th - 1)

    def handle_next_phase(self):
        self._ready_to_advance = False
        self.update_display()

    def _draw_border(self):
        """
        Draw a border around the display area.
        """
        terminal = self.terminal
        tw, th = self.term_size
        terminal.cursorHome()
        terminal.write(gchars.DBORDER_UP_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (tw - 2))
        terminal.write(gchars.DBORDER_UP_RIGHT)
        for n in range(1, th):
            terminal.cursorPosition(0, n)
            terminal.write(gchars.DBORDER_VERTICAL)
            terminal.cursorPosition(tw-1, n)
            terminal.write(gchars.DBORDER_VERTICAL)
        terminal.cursorPosition(0, th - 1)
        terminal.write(gchars.DBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (tw - 2))
        terminal.write(gchars.DBORDER_DOWN_RIGHT)
        title = u"{} Werewolves! {}".format(
            gchars.DHBORDER_UP_RIGHT,
            gchars.DHBORDER_UP_LEFT)
        pos = (tw - len(title)) // 2
        terminal.cursorPosition(pos, 0)
        emca48 = A.bold[
            -A.bold[gchars.DHBORDER_UP_RIGHT.encode('utf-8')],
            " Werewolves! ", 
            -A.bold[gchars.DHBORDER_UP_LEFT.encode('utf-8')]]
        text = assembleFormattedText(emca48)
        terminal.write(text)
        underline = u"{}{}{}".format(
            gchars.DOWN_LEFT_CORNER,
            gchars.HORIZONTAL * (len(title) - 2),
            gchars.DOWN_RIGHT_CORNER)
        terminal.cursorPosition(pos, 1)
        terminal.write(underline)
        pos = tw // 2
        terminal.cursorPosition(pos, 1)
        terminal.write(gchars.T_UP)
        maxrow = max(th // 2, 7)
        terminal.cursorPosition(0, maxrow)
        terminal.write(gchars.DVERT_T_LEFT)
        terminal.write(gchars.HORIZONTAL * (tw - 2))
        terminal.write(gchars.DVERT_T_RIGHT)
        midway = tw // 2
        terminal.cursorPosition(midway, 0)
        terminal.cursorPosition(midway, maxrow)
        terminal.write(gchars.CROSS) 
        for n in range(2, maxrow):
            terminal.cursorPosition(midway, n)
            terminal.write(gchars.VERTICAL)
        for n in range(maxrow + 1, th):
            terminal.cursorPosition(midway, n)
            terminal.write(gchars.VERTICAL)
        terminal.cursorPosition(midway, th)
        terminal.write(gchars.DHORIZ_T_DOWN) 
        self._equator = maxrow
        self._midway = midway
        
    def _draw_player_area(self):
        """
        Show the player name and dealt role.
        """
        player = self.user_id
        terminal = self.terminal
        tw, th = self.term_size
        terminal.cursorPosition(2, 3)
        truncated_player = player[:10]
        emca48 = A.bold["Player: ", -A.bold[truncated_player]]
        text = assembleFormattedText(emca48)
        terminal.write(text)
        terminal.cursorPosition(2, 4)
        game = self.game
        if self.player_cards is None:
            self.player_cards = game.query_player_cards()
        player_cards = self.player_cards
        card = player_cards[player]
        card_name = WerewolfGame.get_card_name(card)
        emca48 = A.bold["Dealt role: ", -A.bold[card_name]]
        text = assembleFormattedText(emca48)
        terminal.write(text)

    def _draw_game_info_area(self):
        """
        Draw the game info area.
        """
        terminal = self.terminal
        tw, th = self.term_size
        equator = self._equator
        game = self.game
        if self.cards is None:
            self.cards = game.query_cards()
        cards = self.cards
        card_counts = collections.Counter()
        for card in cards:
            card_name = WerewolfGame.get_card_name(card)
            card_counts[card_name] += 1
        card_counts = card_counts.items()
        card_counts.sort()
        col_width = max(len(n) for n, c in card_counts) + 3
        count_width = 3
        # heading
        row = 1
        heading = "Cards Used in the Game"
        emca48 = A.bold[heading, -A.bold[""]]
        text = assembleFormattedText(emca48)
        midway = tw // 2
        frame_length = tw - midway
        frame_midway = (frame_length // 2) + midway
        pos = ((frame_length - len(heading)) // 2) + midway
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        # table
        row += 1
        pos = midway + 2
        lit = lambda s: A.reverseVideo[s, -A.reverseVideo[""]]
        unlit = lambda s: -A.reverseVideo[s]
        attribs = itertools.cycle([lit, unlit])
        table_width = col_width + 1 + 5
        pos = midway + ((frame_length - table_width) // 2)
        row += 1
        headers = "{} {}".format("Card".ljust(col_width), "Count")
        emca48 = A.underline[headers, -A.underline[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        g = peek_ahead(zip(card_counts, attribs))
        for ((card_name, count), highlight), more in g:
            row += 1
            terminal.cursorPosition(pos, row)
            if row == (equator - 1):
                terminal.write("more ...")
                break
            if more:
                u = lambda x: x
            else:
                u = lambda x: A.underline[x, -A.underline[""]] 
            emca48 = u(highlight(card_name.rjust(col_width)))
            text = assembleFormattedText(emca48)
            terminal.write(text)
            terminal.write(" ")
            emca48 = u(highlight(str(count).rjust(5)))
            text = assembleFormattedText(emca48)
            terminal.write(text)

    def _draw_phase_area(self):
        """
        Display phase area. 
        """
        terminal = self.terminal
        tw, th = self.term_size
        game = self.game
        phase = game.phase
        if phase == game.PHASE_TWILIGHT:
            self._draw_twilight()
            self.commands = {'*': self._signal_advance}
        elif phase == game.PHASE_WEREWOLVES:
            self._draw_werewolves()
            self.commands = {'\r': self._signal_advance}
        elif phase == game.PHASE_MINION:
            self._draw_minion()
            self.commands = {'\r': self._signal_advance}
        elif phase == game.PHASE_SEER:
            self.commands = {}
            self._draw_seer()
        elif phase == game.PHASE_ROBBER:
            self.commands = {}
            self._draw_robber()
        elif phase == game.PHASE_TROUBLEMAKER:
            self.commands = {}
            self._draw_troublemaker()
        elif phase == game.PHASE_INSOMNIAC:
            self.commands = {}
            self._draw_insomniac()
        self._display_time_remaining()

    def _draw_phase_info(self, title, desc, key_help=None):
        if key_help is None:
            key_help = "Press ENTER to continue ..."
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        row = equator + 1
        pos = (frame_w - len(title)) // 2
        emca48 = A.bold[title, -A.bold[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        lines = wrap_paras(desc, frame_w - 4) 
        maxlen = max(len(line) for line in lines)
        pos = (frame_w - maxlen) // 2
        row += 1
        for line in lines:
            row += 1
            terminal.cursorPosition(pos, row)
            if row == (th - 4):
                terminal.write("...")
                break
            terminal.write(line)
        row = th - 2
        if self._ready_to_advance:
            heading = "Waiting for other players ..."
        else:
            heading = key_help
        pos = (frame_w - len(heading)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(heading)

    def _draw_twilight(self):
        """
        Display game instructions.
        """
        msg = """The village has been invaded by ghastly werewolves!  These bloodthirsty shape changers want to take over the village.  But the villagers know they are weakest at daybreak, and that is when they will strike at their enemy.  In this game, you will take on the role of a villager or a werewolf.  At daybreak, the entire village votes on who lives and who dies.  If a werewolf is slain, the villagers win.  If no werewolves are slain, the werewolf team wins.  If no players are werewolves, the villagers only win if no one dies."""
        self._draw_phase_info(
            "Twilight",
            msg,
            "Press a key to continue ...")

    def _draw_werewolves(self):
        """
        Show the werewolves phase info.
        """
        title = "Werewolf Phase"
        msg = """During this phase, all werewolves open their eyes and look at each other."""
        look_msg = '''You look around and see other werewolves ...'''
        self._impl_werewolf_minion(title, msg, look_msg)

    def _draw_minion(self):
        """
        Show the minion phase info.
        """
        title = "Minion Phase"
        msg = (
            "During this phase, the minion opens his eyes and sees the"
            " werewolves, but they cannot see the minion.")
        look_msg = '''You look around for werewolves ...'''
        self._impl_werewolf_minion(title, msg, look_msg)

    def _impl_werewolf_minion(self, title, msg, look_msg):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        self._draw_phase_info(title, msg)
        game = self.game
        if not game.is_player_active(self.user_id):
            self._display_sleeping()
        else:
            werewolves = game.identify_werewolves()
            werewolves = list(werewolves)
            werewolves.sort()
            row = equator + 1
            pos = midway + 2
            lines = wrap_paras(look_msg, frame_w - 4)
            for line in lines:
                row += 1
                terminal.cursorPosition(pos, row)
                terminal.write(line)
            for player in werewolves:
                row += 1
                terminal.cursorPosition(pos, row)
                if row == (th - 2):
                    terminal.write("...")
                    break
                terminal.write(player)

    def _draw_seer(self):
        """
        The seer can examine 2 cards on the table or a single player's card.
        """
        msg = '''The seer can use her mystic powers to view 1 player's card, or 2 table cards.'''
        game = self.game
        if not game.is_player_active(self.user_id):
            self._draw_phase_info("Seer", msg)
            self._display_sleeping()
            self.commands = {'\r': self._signal_advance}
        elif not game.power_activated:
            key_help = "Choose an option ..."
            self._draw_phase_info("Seer", msg, key_help=key_help)
            self._draw_seer_choose()
        else:
            self._draw_phase_info("Seer", msg)
            self._draw_seer_power_activated()
            
    def _draw_seer_choose(self):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        game = self.game
        commands = {'t': self._seer_examine_table_cards}
        session_entry = session.get_entry(game.session_id)
        members = set(session_entry.members)
        members.discard(self.user_id)
        other_player_list = list(members)
        for n, player in enumerate(other_player_list):
            commands[str(n+1)] = lambda : self._seer_examine_player(player)
            log.msg("DEBUG: {} -> choose {}".format(str(n+1), player))
        row = equator + 2
        pos = midway + 2
        msg = "Choose:"
        terminal.cursorPosition(pos, row)
        terminal.write(msg)
        choices = ['t - Examine 2 table cards.']
        for n, player in enumerate(other_player_list):
            choices.append("{} - Examine {}'s card.".format(n + 1, player))
        for choice in choices:
            row += 1
            terminal.cursorPosition(pos, row)
            terminal.write(choice)
        self.commands = commands

    def _draw_seer_power_activated(self):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        self.commands = {'\r': self._signal_advance}
        game = self.game
        if not game.seer_viewed_table_cards is None:
            # Display table cards.
            cards = game.seer_viewed_table_cards
            card_names = [WerewolfGame.get_card_name(c) for c in cards]
            row = equator + 2
            pos = midway + 2
            msg = "Your mystic powers reveal the following table cards ..." 
            lines = wrap_paras(msg, frame_w - 4)
            for line in lines:
                terminal.cursorPosition(pos, row)
                terminal.write(line)
                row += 1
            row += 1
            for card_name in card_names:
                terminal.cursorPosition(pos, row)
                terminal.write(card_name)
                row += 1
        elif not game.seer_viewed_player_card is None:
            # Display player cards.
            player, card = game.seer_viewed_player_card
            card_name = WerewolfGame.get_card_name(card)
            row = equator + 2
            pos = midway + 2
            msg = "You mystic powers fortell that {} has the {} card.".format(player, card_name)
            lines = wrap_paras(msg, frame_w - 4)
            for line in lines:
                terminal.cursorPosition(pos, row)
                if row == th - 2:
                    terminal.write("...")
                    break
                terminal.write(line)
                row += 1
        else:
            raise Exception("Seer power activated but no cards revealed?!")

    def _seer_examine_table_cards(self):
        game = self.game
        all_positions = [0, 1, 2]
        positions = random.sample(all_positions, 2)
        game.seer_viewed_table_cards = game.seer_view_table_cards(*positions)
        game.power_activated = True

    def _seer_examine_player(self, player):
        game = self.game
        card = game.seer_view_player_card(player)
        game.seer_viewed_player_card = (player, card)
        game.power_activated = True

    def _draw_robber(self):
        log.msg("TODO: _draw_robber()")
        
    def _draw_troublemaker(self):
        log.msg("TODO: _draw_troublemaker()")
        
    def _draw_insomniac(self):
        log.msg("TODO: _draw_insomniac()")
        
    def _display_sleeping(self):
        """
        Display output that player is sleeping during this phase.
        """
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        row = equator + 1
        msg = '''Zzzzz ...  You are sleeping.'''
        pos = midway + (frame_w - len(msg)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(msg)

    def _display_time_remaining(self):
        log.msg("TODO: display_time_remaining()")

    def _signal_advance(self):
        """
        Tell the game that this player has signaled it is OK to advance
        to the next phase.
        """
        user_id = self.user_id
        self.game.signal_advance(user_id)
        self._ready_to_advance = True

def wrap_paras(text, width):
    """
    textwrap.wrap() for multiple paragraphs.
    """
    paras = text.split("\n")
    lines = []
    for para in paras:
        lines.extend(textwrap.wrap(para, width, drop_whitespace=False))
    return lines

def main(stdscr, args):
    """
    Configure and run the werewolf game.
    """
    players = args.player
    werewolf_count, other_roles = parse_roles(args)
    game = WerewolfGame()
    game.add_players(players)
    game.deal_cards(werewolf_count, other_roles)
    display_title(stdscr)
    msg = """The village has been invaded by ghastly werewolves!  These bloodthirsty shape changers want to take over the village.  But the villagers know they are weakest at daybreak, and that is when they will strike at their enemy.  In this game, you will take on the role of a villager or a werewolf.  At daybreak, the entire village votes on who lives and who dies.  If a werewolf is slain, the villagers win.  If no werewolves are slain, the werewolf team wins.  If no players are werewolves, the villagers only win if no one dies."""
    display_text(stdscr, msg, title="Instructions for Play")
    if args.debug:
        debug(game, stdscr)
    show_cards_in_game(stdscr, game)
    show_roles_to_players(game, players, stdscr)
    phase = None
    while True:
        game.advance_phase()
        phase = game.query_phase()
        clear_screen()
        if phase == "Daybreak":
            break
        if not game.is_role_active():
            continue
        for player in players:
            start_player_turn(stdscr, player, phase)
            if not game.is_player_active(player):
                show_player_asleep(stdscr, player, phase)
            elif phase == "Werewolf Phase":
                show_werewolves_to_player(stdscr, game, player, phase)
            elif phase == "Minion Phase":
                show_werewolves_to_player(stdscr, game, player, phase)
            elif phase == "Seer Phase":
                choose_seer_power(stdscr, game, players, player) 
            elif phase == "Robber Phase":
                use_robber_power(stdscr, game, players, player)
            elif phase == "Troublemaker Phase":
                use_troublemaker_power(stdscr, game, players, player)
            elif phase == "Insomniac Phase":
                wake_up_insomniac(stdscr, game, player)
            else:
                raise Exception("Unknown phase, {}".format(phase))
    show_daybreak_message(stdscr)
    vote_to_eliminate(stdscr, game, players)
    display_post_game_results(stdscr, game, players)

def parse_roles(args):
    """
    Determine which roles should be included in the game deck
    and how many werewolf cards should be present.

    Returns tuple (werewolf count, roles).
    """
    wg = WerewolfGame
    deck = set([
        wg.CARD_SEER,
        wg.CARD_ROBBER,
        wg.CARD_TROUBLEMAKER
    ]) 
    if args.exclude_seer:
        deck.discard(wg.CARD_SEER)
    if args.exclude_robber:
        deck.discard(wg.CARD_ROBBER)
    if args.exclude_troublemaker:
        deck.discard(wg.CARD_TROUBLEMAKER)
    if args.minion:
        deck.add(wg.CARD_MINION)
    if args.insomniac:
        deck.add(wg.CARD_INSOMNIAC)
    if args.hunter:
        deck.add(wg.CARD_HUNTER)
    if args.tanner:
        deck.add(wg.CARD_TANNER)
    return (args.werewolves, deck)

def show_cards_in_game(stdscr, game):
    """
    Show what cards will be used in the game.
    """
    cards = game.query_cards()
    card_counts = collections.Counter()
    for card in cards:
        card_name = WerewolfGame.get_card_name(card)
        card_counts[card_name] += 1
    card_counts = card_counts.items()
    card_counts.sort()
    col_width = max(len(n) for n, c in card_counts) + 3 
    count_width = 3
    lines = []
    lines.append("======================")
    lines.append("Cards Used in the Game")
    lines.append("======================")
    lines.append(" ")
    for card_name, count in card_counts:
        lines.append("* {} x{}".format(card_name.rjust(col_width), str(count).rjust(3)))
    msg = '\n'.join(lines)
    display_text(
        stdscr, 
        msg,
        title="= Setup =", 
        keys=[curses.KEY_ENTER, 10, 13],
        key_message="= Press ENTER =")

def start_player_turn(stdscr, player, phase):
    """
    Start a player's turn.
    """
    display_text(
        stdscr, 
        "Press ENTER to start {}'s turn.".format(player), 
        title=phase, 
        keys=[curses.KEY_ENTER, 10, 13],
        key_message="= Press ENTER =")

def show_player_asleep(stdscr, player, phase):
    """
    Notify the player that (s)he is asleep.
    """
    display_text(
        stdscr, 
        "Zzzzzzzzzz ... {}, you are asleep.".format(player), 
        title=phase, 
        keys=[curses.KEY_ENTER, 10, 13],
        key_message="= Press ENTER =")

def show_werewolves_to_player(stdscr, game, player, phase):
    """
    Notify a werewolf player who else is looking around.
    """
    lines = []
    if phase == "Werewolf Phase":
        lines.append("{}, you look around and see other werewolves:".format(player))
    else:
        lines.append("{}, you look around and see the werewolves:".format(player))
    werewolves = game.identify_werewolves()
    for ww in werewolves:
        lines.append("* {}".format(ww))
    msg = '\n'.join(lines)
    display_text(
        stdscr, 
        msg, 
        title=phase, 
        keys=[curses.KEY_ENTER, 10, 13],
        key_message="= Press ENTER =")

def show_daybreak_message(stdscr):
    """
    Show the daybreak phases.
    """
    msg = textwrap.dedent("""\
    You've made it to daybreak!  It's time to discuss what happened during the
    night and vote for which player should be eliminated.  It is recommended
    you set a time limit of about 5 minutes.  Once the all players are finished
    talking, press any key to start voting.
    """)
    display_text(
        stdscr,
        msg,
        title="Daybreak")

def vote_to_eliminate(stdscr, game, players):
    """
    Vote to eliminate a player.
    """
    votes = collections.Counter()
    hunter = game.query_hunter()
    hunter_victim = None
    for player in players:
        lines = []
        player_map = {}
        keys = []
        n = 1
        lines.append("{}, cast your vote to eliminate which player?".format(player))
        for oplayer in players:
            label = oplayer
            if player == oplayer:
                label = "myself"
            lines.append("{}) {}".format(n, label))
            player_map[n] = oplayer
            keys.append(ord(str(n)))
            n += 1
        rval = display_text(
            stdscr,
            '\n'.join(lines),
            title="Daybreak",
            keys=keys,
            key_message="= Choose a player =")
        choice = int(chr(rval))
        oplayer = player_map[choice]
        if player == hunter:
            hunter_victim = oplayer
        votes[oplayer] += 1
    rank = votes.most_common()
    most_votes = []
    top_score = 0
    for player, count in rank:
        if count == 1:
            break
        if count < top_score:
            break
        top_score = count
        most_votes.append(player)
    if hunter in most_votes:
        most_votes.append(hunter_victim)
        most_votes = list(set(most_votes))
        most_votes.sort()
    game.eliminate_players(most_votes)
    if len(most_votes) == 0:
        msg = "No one was eliminated!"
    elif len(most_votes) == 1:
        msg = "{} has been eliminated!".format(most_votes[0])
    elif len(most_votes) == 2:
        msg = "{} and {} have been eliminated!".format(*most_votes)
    else:
        msg = "{} and {} have been eliminated!".format(', '.join(most_votes[:-1]), most_votes[-1])
    display_text(
        stdscr,
        msg,
        title="Daybreak"
    )

def display_post_game_results(stdscr, game, players):
    """
    Display post-game results.
    """
    results = game.query_post_game_results() 
    winning_team = results.winner
    if winning_team == WerewolfGame.WINNER_VILLAGE:
        title = "Village Victory!"
    elif winning_team == WerewolfGame.WINNER_TANNER_AND_VILLAGE:
        title = "Village & Tanner Victory!"
    elif winning_team == WerewolfGame.WINNER_TANNER:
        title = "Tanner Victory!"
    elif winning_team == WerewolfGame.WINNER_WEREWOLVES:
        title = "Werewolf Victory!"
    elif winning_team == WerewolfGame.WINNER_NO_ONE:
        title = "No one wins!"
    else:
        raise Exception("Unknown winner code {}".format(winning_team))
    player_result_matrix = []
    for player in players:
        entry = (
            player,
            WerewolfGame.get_card_name(results.orig_player_cards[player]),
            WerewolfGame.get_card_name(results.player_cards[player]))
        player_result_matrix.append(entry)
    table_result_matrix = zip(
        [WerewolfGame.get_card_name(c) for c in results.orig_table_cards],
        [WerewolfGame.get_card_name(c) for c in results.table_cards])
    lines = []
    col_width = 20
    col_space = 2
    lines.append("- Player Results -".center(col_width * 3))
    lines.append(" ")
    lines.append("{}{}{}".format(
        "Player".ljust(col_width),
        "Dealt Card".ljust(col_width),
        "Final Card".ljust(col_width)))
    lines.append("{}{}{}".format(
        ("=" * (col_width - col_space)).ljust(col_width),
        ("=" * (col_width - col_space)).ljust(col_width),
        ("=" * (col_width - col_space)).ljust(col_width)))
    cycle_it = itertools.cycle([False, True])
    for highlight, (player, dealt, final) in six.moves.zip(cycle_it, player_result_matrix):
        lines.append("{}{}{}".format(
            player.ljust(col_width),
            dealt.ljust(col_width),
            final.ljust(col_width)))
    lines.append(" ")
    lines.append("- Cards Dealt to the Table -".center(col_width * 3))
    lines.append(" ")
    lines.append("{}{}{}".format(
        "Table Spot".ljust(col_width),
        "Dealt Card".ljust(col_width),
        "Final Card".ljust(col_width)))
    lines.append("{}{}{}".format(
        ("=" * (col_width - col_space)).ljust(col_width),
        ("=" * (col_width - col_space)).ljust(col_width),
        ("=" * (col_width - col_space)).ljust(col_width)))
    cycle_it = itertools.cycle([False, True])
    for n, (highlight, (dealt, final)) in enumerate(six.moves.zip(cycle_it, table_result_matrix)):
        lines.append("{}{}{}".format(
            ("Card {}".format(n + 1)).ljust(col_width),
            dealt.ljust(col_width),
            final.ljust(col_width)))
    display_text(
        stdscr,
        '\n'.join(lines),
        title=title)

def choose_seer_power(stdscr, game, players, player):
    msg = textwrap.dedent("""\
    {}, choose:

    1) Look at a player's card.
    2) Look at 2 table cards.
    """).format(player)
    rval = display_text(
        stdscr,
        msg,
        title="Seer Phase",
        keys=[ord("1"), ord("2")],
        key_message="= Choose 1 or 2 =")
    if rval == ord("1"):
        lines = []
        lines.append("View which player's card?")
        lines.append("")
        n = 1
        keys = []
        oplayer_map = {}
        for oplayer in players:
            if oplayer == player:
                continue
            lines.append("{}) {}".format(n, oplayer))
            key_code = ord("{}".format(n))
            keys.append(key_code)
            oplayer_map[key_code] = oplayer
            n += 1
        rval = display_text(
            stdscr,
            '\n'.join(lines),
            title="Seer Phase",
            keys=keys,
            key_message="= Choose a player =") 
        oplayer = oplayer_map[rval]
        card_code = game.seer_view_player_card(oplayer)
        card_name = WerewolfGame.get_card_name(card_code)
        display_text(
            stdscr,
            "{}'s card is {}.".format(oplayer, card_name),
            title="Seer Phase")
    elif rval == ord("2"):
        all_choices = [ord("1"), ord("2"), ord("3")]
        chosen = []
        while len(chosen) != 2:
            if len(chosen) == 0:
                msg = "Choose a table card."
            else:
                msg = "Choose another table card."
            keys = [k for k in all_choices if k not in chosen]
            key_message = "= Choose {} =".format(', '.join(chr(k) for k in keys))
            rval = display_text(
                stdscr,
                msg,
                title="Seer Phase",
                keys=keys,
                key_message=key_message)
            chosen.append(rval)
        choices = [int(chr(code)) - 1 for code in chosen]
        cards = game.seer_view_table_cards(*choices)
        card_names = [WerewolfGame.get_card_name(card) for card in cards]
        msg = textwrap.dedent("""\
        Your mystic powers reveal the following table cards:

        * Card {} is {}.
        * Card {} is {}.
        """).format(choices[0]+1, card_names[0], choices[1]+1, card_names[1])
        display_text(
            stdscr,
            msg,
            title="Seer Phase")

def use_robber_power(stdscr, game, players, player):
    """
    Use the Robber's power to steal a card.
    """
    lines = []
    player_map = {}
    lines.append("{}, exchange your Robber card for another player's card.".format(player))
    lines.append("Exchange with which player?")
    lines.append("1) I'll keep my card.")
    n = 2
    for oplayer in players:
        if oplayer == player:
            continue
        lines.append("{}) {}".format(n, oplayer))
        player_map[n] = oplayer
        n += 1
    msg = '\n'.join(lines)
    player_map[1] = player
    keys = [ord("{}".format(n)) for n in player_map.keys()]
    rval = display_text(
        stdscr,
        msg,
        title="Robber Phase", 
        keys=keys,
        key_message="= Choose an Option =")
    if int(chr(rval)) == 1:
        return
    oplayer = player_map[int(chr(rval))]
    stolen_card = game.robber_steal_card(oplayer)
    card_name = WerewolfGame.get_card_name(stolen_card)
    display_text(
        stdscr,
        "{}, you stole the {} card from {}!".format(player, card_name, oplayer),
        title="Robber Phase", 
        keys=[curses.KEY_ENTER, 10, 13],
        key_message="= Press ENTER =")

def use_troublemaker_power(stdscr, game, players, player):
    """
    Use the Troublemaker's power to switch 2 player's cards.
    """
    lines = []
    player_map = {}
    lines.append("{}, exchange 2 other players' cards.".format(player))
    lines.append("Exchange with which player?")
    lines.append("1) I've decided not to meddle.")
    n = 2
    for oplayer in players:
        if oplayer == player:
            continue
        lines.append("{}) {}".format(n, oplayer))
        player_map[n] = oplayer
        n += 1
    msg = '\n'.join(lines)
    player_map[1] = player
    keys = [ord("{}".format(n)) for n in player_map.keys()]
    rval = display_text(
        stdscr,
        msg,
        title="Troublemaker Phase", 
        keys=keys,
        key_message="= Choose an Option =")
    choice = int(chr(rval))
    if choice == 1:
        return
    oplayer_a = player_map[choice]
    n = 1
    player_map = {}
    lines = []
    lines.append("Choose a 2nd player.")
    for oplayer in players:
        if oplayer == player:
            continue
        if oplayer == oplayer_a:
            continue
        lines.append("{}) {}".format(n, oplayer))
        player_map[n] = oplayer
        n += 1
    msg = '\n'.join(lines)
    rval = display_text(
        stdscr,
        msg,
        title="Troublemaker Phase", 
        keys=[ord("{}".format(n)) for n in player_map.keys()],
        key_message="= Choose an Option =")
    choice = int(chr(rval))
    oplayer_b = player_map[choice]
    game.troublemaker_switch_cards(oplayer_a, oplayer_b)
    display_text(
        stdscr,
        "{}, you switched cards for {} and {}.".format(player, oplayer_a, oplayer_b),
        title="Troublemaker Phase")

def wake_up_insomniac(stdscr, game, player):
    """
    Notify insomniac what her current card is.
    """
    card = game.insomniac_view_card()
    card_name = WerewolfGame.get_card_name(card)
    msg = textwrap.dedent("""\
    {}, your card is {}.
    """).format(player, card_name)
    display_text(
        stdscr, 
        msg, 
        title="Insomniac Phase", 
        keys=[curses.KEY_ENTER, 10, 13],
        key_message="= Press ENTER =")

def display_title(stdscr):
    """
    Display the title.
    """
    h, w = stdscr.getmaxyx()
    stdscr.border()
    title = "Werewolves!"
    x = int(((w-2) - len(title)) / 2)
    stdscr.addstr(1, x, "Werewolves!", curses.A_REVERSE)
    stdscr.refresh()

def display_text(stdscr, msg, title=None, keys=None, key_message="= PRESS A KEY ="):
    """
    Display a message in the message area and wait for a keypress.
    """
    h, w = stdscr.getmaxyx()
    dialog_w = int(w * 0.67)
    lines = []
    paras = msg.split('\n')
    for para in paras:
        lines.extend(textwrap.wrap(para, dialog_w - 4, drop_whitespace=False))
    line_count = len(lines)
    max_width = max(len(l) for l in lines)
    if key_message is not None:
        max_width = max(max_width, len(key_message))
    dialog_w = min(max_width + 4, dialog_w)
    dialog_h = line_count + 3
    if key_message is not None:
        dialog_h += 2
    dialog_size = (line_count + 5, dialog_w)
    dialog_h, dialog_w = dialog_size
    dialog_h = min(h, dialog_h)
    dialog_w = min(w, dialog_w)
    x = int((w - dialog_w) / 2)
    y = int((h - dialog_h) / 2)
    win = curses.newwin(dialog_h, dialog_w, y, x)
    win.border()
    for n, line in enumerate(lines):
        win.addstr((n + 2), 2, line)
    if key_message is not None: 
        press = key_message
        press_size = len(press)
        press_x = int((dialog_w - press_size) / 2)
        win.addstr(dialog_h-2, press_x, press, curses.A_BOLD)
    if title is not None:
        title_size = len(title)
        title_x = int((dialog_w - title_size) / 2)
        win.addstr(0, title_x, title, curses.A_STANDOUT)
    win.refresh()
    if keys is not None:
        keys = set(keys)
    while True:
        c = stdscr.getch(1, 0)
        if keys is None:
            break
        if c in keys:
            break
    win.clear()
    win.refresh()
    return c

def clear_screen():
    pass

def show_active_players(game, players):
    print("The following players are active:")
    for player in players:
        if game.is_player_active(player):
            print("* {}".format(player))

def debug(game, stdscr):
    """
    Dump state for debugging.
    """
    player_cards = game.query_player_cards()
    lines = []
    lines.append("Player cards:")
    for player, card in player_cards.items():
        lines.append("{} -> {}".format(player, WerewolfGame.get_card_name(card)))
    lines.append("Table cards:")
    table_cards = game.query_table_cards()
    for n, card in enumerate(table_cards):
        lines.append("Table {} -> {}".format(n+1, WerewolfGame.get_card_name(card)))
    text = '\n'.join(lines)
    display_text(stdscr, text, title="DEBUG Info") 

def show_roles_to_players(game, players, stdscr):
    """
    Show each player the role he or she was dealt.
    """
    player_cards = game.query_player_cards()
    for player in players:
        display_text(
            stdscr, 
            "{}'s turn.".format(player), 
            title="The Deal", 
            keys=[curses.KEY_ENTER, 10, 13], 
            key_message="= Press ENTER =") 
        display_text(
            stdscr, 
            "{} was dealt {}".format(player, WerewolfGame.get_card_name(player_cards[player])), 
            title="The Deal", 
            keys=[curses.KEY_ENTER, 10, 13], 
            key_message="= Press ENTER =") 

def required_length(nmin, nmax):


    class RequiredLength(argparse.Action):

        def __call__(self, parser, args, values, option_string=None):
            if (not len(values) >= nmin) or (not len(values) <= nmax):
                msg='argument "{f}" requires between {nmin} and {nmax} arguments'.format(
                    f=self.dest,
                    nmin=nmin,
                    nmax=nmax)
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)


    return RequiredLength

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Werewolves! game')
    parser.add_argument(
        'player', 
        metavar='PLAYER', 
        action=required_length(3, 10),
        nargs='+',
        help='A player.  Between 3 and 10 players can be specified.')
    parser.add_argument(
        '-d',
        '--debug',
        action="store_true",
        help="Turn on debugging.")
    parser.add_argument(
        '-W',
        '--werewolves',
        action="store",
        default=2,
        type=int,
        help='The number of werewolves to include (default 2).')
    parser.add_argument(
        '--exclude-seer',
        action="store_true",
        help='Exclude the seer role.')
    parser.add_argument(
        '--exclude-robber',
        action="store_true",
        help='Exclude the robber role.')
    parser.add_argument(
        '--exclude-troublemaker',
        action="store_true",
        help='Exclude the troublemaker role.')
    parser.add_argument(
        '-M',
        '--minion',
        action="store_true",
        help='Include the minion role.')
    parser.add_argument(
        '-I',
        '--insomniac',
        action="store_true",
        help='Include the insomniac role.')
    parser.add_argument(
        '-H',
        '--hunter',
        action="store_true",
        help='Include the insomniac role.')
    parser.add_argument(
        '-T',
        '--tanner',
        action="store_true",
        help='Include the tanner role.')
    try:
        args = parser.parse_args()
    except argparse.ArgumentTypeError as ex:
        parser.error(str(ex))
    curses.wrapper(main, args)

def peek_ahead(iterable):
    """
    yield (value, more) from an iterable where `more` is a boolean value that
    indicates if there is another value yet to be yielded.
    """
    flag = False
    prev_value = None
    for value in iterable:
        if not flag:
            flag = True
            prev_value = value
            continue
        yield (prev_value, True)
        prev_value = value
    yield (prev_value, False)
        
