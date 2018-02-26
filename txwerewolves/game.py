
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import collections
import itertools
import json
import random
import sys
import textwrap
import weakref
from txwerewolves.apps import (
    TerminalAppBase,
    WebAppBase,
)
from txwerewolves.dialogs import (
    BriefMessageDialog,
    ChatDialog,
    HelpDialog,
    SessionAdminDialog,
    SystemMessageDialog,
)
from txwerewolves import graphics_chars as gchars
from txwerewolves.interfaces import (
    ITerminalApplication,
    IWebApplication,
)
from txwerewolves import (
    session,
    users,
)
from txwerewolves.utils import (
    wrap_paras,
    peek_ahead
)
from txwerewolves.werewolf import WerewolfGame
import six
from six.moves import (
    zip,
)
from twisted.python import log
from twisted.conch.insults.text import (
    attributes as A,
    assembleFormattedText,
)
from zope import interface


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
    player_cards = None
    used_roles = None
    power_activated = False
    seer_viewed_table_cards = None
    seer_viewed_player_card = None
    robber_stolen_card = None
    troublemaker_swapped_players = None
    votes = None
    post_game_results = None
    eliminated = None

    # --------------
    # Event handlers
    # --------------

    def handle_cards_dealt(self):
        log.msg("Cards have been dealt.")
        self.phase = self.PHASE_TWILIGHT
        self.player_cards = self.query_player_cards()
        table_cards = self.query_table_cards()
        self.used_roles = frozenset(table_cards + list(self.player_cards.values()))
        self.set_wait_list()
        self.notify_players()

    def handle_werewolf_phase(self):
        log.msg("Entered the werewolf phase.")
        if not self.CARD_WEREWOLF in self.used_roles:
            self.advance_phase()
            return
        self.phase = self.PHASE_WEREWOLVES
        self.set_wait_list()
        self.notify_players()

    def handle_minion_phase(self):
        log.msg("Entered the minion phase.")
        if not self.CARD_MINION in self.used_roles:
            self.advance_phase()
            return
        self.phase = self.PHASE_MINION
        self.set_wait_list()
        self.notify_players()
    
    def handle_seer_phase(self):
        log.msg("Entered the seer phase.")
        if not self.CARD_SEER in self.used_roles:
            self.advance_phase()
            return
        self.phase = self.PHASE_SEER
        self.power_activated = False
        self.set_wait_list()
        self.notify_players()
    
    def handle_robber_phase(self):
        log.msg("Entered the robber phase.")
        if not self.CARD_ROBBER in self.used_roles:
            self.advance_phase()
            return
        self.phase = self.PHASE_ROBBER
        self.power_activated = False
        self.set_wait_list()
        self.notify_players()
    
    def handle_troublemaker_phase(self):
        log.msg("Entered the troublemaker phase.")
        if not self.CARD_TROUBLEMAKER in self.used_roles:
            self.advance_phase()
            return
        self.phase = self.PHASE_TROUBLEMAKER
        self.power_activated = False
        self.set_wait_list()
        self.notify_players()
    
    def handle_insomniac_phase(self):
        log.msg("Entered the insomniac phase.")
        if not self.CARD_INSOMNIAC in self.used_roles:
            self.advance_phase()
            return
        self.phase = self.PHASE_INSOMNIAC
        self.set_wait_list()
        self.notify_players()
    
    def handle_daybreak(self):
        log.msg("Entered daybreak phase.")
        self.votes = {}
        self.phase = self.PHASE_DAYBREAK
        self.set_wait_list()
        self.notify_players()
    
    def handle_endgame(self):
        log.msg("Entered the endgame phase.")
        self.phase = self.PHASE_ENDGAME
        self.set_wait_list()
        self.post_game_results = self.query_post_game_results()
        self.notify_players()

    # ---------
    # Signaling
    # ---------

    def notify_players(self):
        """
        Notify all connected players that a change in game state has occured
        and they should update their UIs.
        """
        signal = ('next-phase', None)
        session.send_signal_to_members(self.session_id, signal)

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
            if self.phase != self.PHASE_DAYBREAK:
                self.advance_phase()
            else:
                self.count_votes()

    def count_votes(self):
        """
        Count the votes, determine who won and who lost.
        """
        vote_map = self.votes
        votes = collections.Counter()
        hunter = self.query_hunter()
        hunter_victim = None
        for voter, player in vote_map.items():
            votes[player] += 1
            if voter == hunter:
                hunter_victim = player
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
        self.eliminated = list(most_votes)
        self.eliminate_players(most_votes)
            
    

class SSHGameProtocol(TerminalAppBase):
    interface.implements(ITerminalApplication)

    cards = None
    commands = None
    game = None
    input_buf = None
    new_chat_flag = False
    player_cards = None
    _ready_to_advance = False
    _shutting_down = False

    @classmethod
    def make_protocol(klass, **kwds):
        instance = klass()
        for k, v in kwds.items():
            if hasattr(instance, k):
                setattr(instance, k, v)
        instance.commands = {}
        entry = users.get_user_entry(instance.user_id)
        session_entry = session.get_entry(entry.joined_id)
        if session_entry.appstate is None or kwds.get('reset', False):
            players = session_entry.members
            game = HandledWerewolfGame()
            session_entry.appstate = game
            game.session_id = session_entry.session_id
            game.add_players(players)
            werewolf_count = kwds.get('werewolves', 2)
            wg = WerewolfGame
            other_roles = kwds.get('roles', set([
                wg.CARD_SEER,
                wg.CARD_ROBBER,
                wg.CARD_TROUBLEMAKER,
                wg.CARD_MINION,
                wg.CARD_INSOMNIAC,
                wg.CARD_HUNTER,
                wg.CARD_TANNER,
            ]))
            instance.reactor.callLater(
                0, game.deal_cards, werewolf_count, other_roles)
        instance.game = session_entry.appstate
        instance.input_buf = []
        return instance

    @property
    def appstate(self):
        """
        Application interface.
        Return the machine that drives the application.
        """
        return self.game

    def handle_input(self, key_id, modifier):
        """
        Handle user input.
        """ 
        handled = False
        ORD_TAB = 9
        ORD_CTRL_A = 1
        dialog = self.dialog
        if not handled and not dialog is None:
            handled = dialog.handle_input(key_id, modifier)
        if not handled and key_id == 'h':
            self._show_help()
            handled = True
        if not handled and ord(key_id) == ORD_TAB:
            self._show_chat()
            handled = True
        if not handled and ord(key_id) == ORD_CTRL_A:
            self._show_session_admin()
            handled = True
        if not handled and not self.commands is None:
            commands = self.commands
            func = commands.get(key_id)
            if func is None:
                func = commands.get('*', None)
            if not func is None:
                func()
                self.update_display()
        #self.update_display() 

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
        if not self.dialog is None:
            self.dialog.draw()
        dialog = self.dialog
        if dialog is not None:
            handled = dialog.set_cursor_pos()
        else:
            handled = False
        if not handled:
            self.set_cursor_end_pos()

    def set_cursor_end_pos(self):
        tw, th = self.term_size
        terminal = self.terminal
        terminal.cursorPosition(0, th - 1)

    def _handle_next_phase(self):
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
        pos = 2
        row = 3
        terminal.cursorPosition(pos, row)
        truncated_player = player[:10]
        emca48 = A.bold["Player: ", -A.bold[truncated_player]]
        text = assembleFormattedText(emca48)
        terminal.write(text)
        row += 1
        terminal.cursorPosition(pos, row)
        game = self.game
        player_cards = game.player_cards
        card = player_cards[player]
        card_name = WerewolfGame.get_card_name(card)
        emca48 = A.bold["Dealt role: ", -A.bold[card_name]]
        text = assembleFormattedText(emca48)
        terminal.write(text)
        if self.new_chat_flag:
            row += 1
            emca48 = A.bold["New chat message", -A.bold[""]]
            text = assembleFormattedText(emca48)
            terminal.cursorPosition(pos, row)
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
        self.commands = None
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
            self._draw_seer()
        elif phase == game.PHASE_ROBBER:
            self._draw_robber()
        elif phase == game.PHASE_TROUBLEMAKER:
            self._draw_troublemaker()
        elif phase == game.PHASE_INSOMNIAC:
            self.commands = {'\r': self._signal_advance}
            self._draw_insomniac()
        elif phase == game.PHASE_DAYBREAK:
            self._draw_daybreak()
        elif phase == game.PHASE_ENDGAME:
            self._draw_endgame()
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
        last_row = row
        row = th - 2
        if self._ready_to_advance:
            heading = "Waiting for other players ..."
        else:
            heading = key_help
        pos = (frame_w - len(heading)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(heading)
        return last_row

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
            self._draw_phase_info("Seer Phase", msg)
            self._display_sleeping()
            self.commands = {'\r': self._signal_advance}
        elif not game.power_activated:
            key_help = "Choose an option ..."
            self._draw_phase_info("Seer Phase", msg, key_help=key_help)
            self._draw_seer_choose()
        else:
            self._draw_phase_info("Seer Phase", msg)
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

            def _make_command(player):
                return lambda : self._seer_examine_player(player)

            commands[str(n+1)] = _make_command(player)
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
        """
        The robber may choose to exchange his card with another player's card.
        """
        msg = """The robber may exchange his card with another player's card.  He looks at the card he has robbed, and is now on that team.  The player receiving the robber card is on the village team."""
        game = self.game
        if not game.is_player_active(self.user_id):
            self._draw_phase_info("Robber Phase", msg)
            self._display_sleeping()
            self.commands = {'\r': self._signal_advance}
        elif not game.power_activated:
            key_help = "Choose an option ..."
            self._draw_phase_info("Robber Phase", msg, key_help=key_help)
            self._draw_robber_choose()
        else:
            self._draw_phase_info("Robber Phase", msg)
            self._draw_robber_power_activated()
        
    def _draw_robber_choose(self):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        game = self.game
        commands = {'x': self._robber_dont_steal}
        session_entry = session.get_entry(game.session_id)
        members = set(session_entry.members)
        members.discard(self.user_id)
        other_player_list = list(members)
        for n, player in enumerate(other_player_list):

            def _make_command(player):
                return lambda : self._robber_steal_from_player(player)

            commands[str(n+1)] = _make_command(player)
        row = equator + 2
        pos = midway + 2
        msg = "Choose:"
        terminal.cursorPosition(pos, row)
        terminal.write(msg)
        choices = ["x - Don't rob anyone."]
        for n, player in enumerate(other_player_list):
            choices.append("{} - Rob {}'s card.".format(n + 1, player))
        for choice in choices:
            row += 1
            terminal.cursorPosition(pos, row)
            terminal.write(choice)
        self.commands = commands

    def _draw_robber_power_activated(self):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        self.commands = {'\r': self._signal_advance}
        game = self.game
        if not game.robber_stolen_card is None:
            # Display stolen card.
            player, card = game.robber_stolen_card
            card_name = WerewolfGame.get_card_name(card)
            row = equator + 2
            pos = midway + 2
            msg = "You stole the {} card from {}.".format(card_name, player) 
            lines = wrap_paras(msg, frame_w - 4)
            for line in lines:
                terminal.cursorPosition(pos, row)
                terminal.write(line)
                row += 1
            row += 1
        else:
            row = equator + 2
            pos = midway + 2
            msg = "You chose not to steal."
            lines = wrap_paras(msg, frame_w - 4)
            for line in lines:
                terminal.cursorPosition(pos, row)
                if row == th - 2:
                    terminal.write("...")
                    break
                terminal.write(line)
                row += 1

    def _robber_dont_steal(self):
        log.msg("Robber chose not to steal.")
        self.game.power_activated = True

    def _robber_steal_from_player(self, player):
        log.msg("Robber stole from {}".format(player))
        game = self.game
        game.power_activated = True
        card = game.robber_steal_card(player)
        game.robber_stolen_card = (player, card)

    def _draw_troublemaker(self):
        """
        The troublemaker may exchange the cards of 2 other players without
        looking at them.
        """
        msg = """The troublemaker may exchange the cards of 2 other players without looking at them."""
        game = self.game
        if not game.is_player_active(self.user_id):
            self._draw_phase_info("Troublemaker Phase", msg)
            self._display_sleeping()
            self.commands = {'\r': self._signal_advance}
        elif not game.power_activated:
            key_help = "Choose an option ..."
            self._draw_phase_info("Troublemaker Phase", msg, key_help=key_help)
            self._draw_troublemaker_choose()
        else:
            self._draw_phase_info("Troublemaker Phase", msg)
            self._draw_troublemaker_power_activated()
        
    def _draw_troublemaker_choose(self):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        game = self.game
        commands = {'x': self._troublemaker_dont_cause_trouble}
        session_entry = session.get_entry(game.session_id)
        members = set(session_entry.members)
        members.discard(self.user_id)
        first_choice = game.troublemaker_swapped_players
        other_player_list = list(members)
        for n, player in enumerate(other_player_list):

            def _make_command(player):
                return lambda : self._troublemaker_switch_player_card(player)

            if player != first_choice:
                commands[str(n+1)] = _make_command(player)
        row = equator + 2
        pos = midway + 2
        msg = "Choose:"
        terminal.cursorPosition(pos, row)
        terminal.write(msg)
        choices = ["x - Don't cause trouble."]
        for n, player in enumerate(other_player_list):
            if first_choice is None:
                choices.append("{} - Exchange {}'s card ...".format(n + 1, player))
            else:
                if player == first_choice:
                    choices.append("{} - already selected {}".format(" " * len(str(n+1)), player))
                else:
                    choices.append("{} - Exchange {}'s card with {}'s card.".format(
                        n + 1, first_choice, player))
        for choice in choices:
            row += 1
            terminal.cursorPosition(pos, row)
            terminal.write(choice)
        self.commands = commands

    def _draw_troublemaker_power_activated(self):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        self.commands = {'\r': self._signal_advance}
        game = self.game
        if not game.troublemaker_swapped_players is None:
            player1, player2 = game.troublemaker_swapped_players
            row = equator + 2
            pos = midway + 2
            msg = "You swapped {}'s card with {}'s card.".format(player1, player2) 
            lines = wrap_paras(msg, frame_w - 4)
            for line in lines:
                terminal.cursorPosition(pos, row)
                terminal.write(line)
                row += 1
            row += 1
        else:
            row = equator + 2
            pos = midway + 2
            msg = "You chose not to cause trouble."
            lines = wrap_paras(msg, frame_w - 4)
            for line in lines:
                terminal.cursorPosition(pos, row)
                if row == th - 2:
                    terminal.write("...")
                    break
                terminal.write(line)
                row += 1

    def _troublemaker_dont_cause_trouble(self):
        log.msg("Troublemaker chose not to exchange cards.")
        self.troublemaker_swapped_players = None
        self.game.power_activated = True

    def _troublemaker_switch_player_card(self, player):
        log.msg("Troublemaker chose player {}".format(player))
        game = self.game
        if game.troublemaker_swapped_players is None:
            game.troublemaker_swapped_players = player
        else:
            player1 = game.troublemaker_swapped_players
            game.troublemaker_swapped_players = (player1, player)
            game.troublemaker_switch_cards(player1, player)
            game.power_activated = True
        
    def _draw_insomniac(self):
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        title = "Insomniac Phase"
        msg = """The insomniac wakes up in the middle of the night and checks to see if her card has been changed."""
        self._draw_phase_info(title, msg)
        game = self.game
        if not game.is_player_active(self.user_id):
            self._display_sleeping()
        else:
            row = equator + 2
            pos = midway + 2
            card = game.insomniac_view_card()
            if card == WerewolfGame.CARD_INSOMNIAC:
                text = "Your card has NOT changed."
            else:
                card_name = WerewolfGame.get_card_name(card)
                text = "Your card has been switched with the {} card!".format(card_name)
            lines = wrap_paras(text, frame_w - 4)
            for line in lines:
                if row == th - 2:
                    terminal.write("...")
                    break
                terminal.cursorPosition(pos, row)
                terminal.write(line)
                row += 1

    def _draw_daybreak(self):
        """
        At daybreak, everyone discusses what happened and votes who to eliminate.
        """
        msg = """It is now daybreak.  Everyone should discuss what happened the night before.  Each player will then have one vote to decide who should be eliminated.  If at least 1 player has more than 1 vote, the player with the most votes is eliminated!"""
        user_id = self.user_id
        game = self.game
        card = game.player_cards[user_id]
        if card == WerewolfGame.CARD_HUNTER:
            msg += "\n\nIf the hunter is eliminated, the player he voted for is also eliminated." 
        elif card == WerewolfGame.CARD_TANNER:
            msg += "\n\nThe tanner only wins if he is eliminated." 
        self._draw_phase_info(
            "Daybreak",
            msg,
            "Vote!")
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        session_entry = session.get_entry(game.session_id)
        members = set(session_entry.members)
        players = list(members)
        players.sort()
        commands = {}
        user_id = self.user_id
        for n, player in enumerate(players):
            
            def _make_command(player):
                return lambda : self._daybreak_vote_for_player(player)

            commands[str(n + 1)] = _make_command(player)
        self.commands = commands
        pos = midway + 2
        row = equator + 2
        terminal.cursorPosition(pos, row)
        msg = "Vote to eliminate player ..."
        terminal.write(msg)
        row += 1
        for n, player in enumerate(players):
            if row == th - 2:
                terminal.write("...")
                break
            terminal.cursorPosition(pos, row)
            if player == user_id:
                msg = "{} - yourself".format(n + 1)
            else:
                msg = "{} - {}".format(n + 1, player)
            terminal.write(msg)
            row += 1

    def _daybreak_vote_for_player(self, player):
        game = self.game
        votes = game.votes
        user_id = self.user_id
        votes[user_id] = player
        log.msg("{} voted to eliminate {}".format(user_id, player))
        self._signal_advance()
    
    def _draw_endgame(self):
        msg = """The game is now over.  Time to see who won!"""
        user_id = self.user_id
        last_row = self._draw_phase_info(
            "Post Game Results",
            msg,
            "")
        terminal = self.terminal
        tw, th = self.term_size
        midway = tw // 2
        equator = th // 2
        frame_w = tw - midway
        game = self.game
        eliminated = set(game.eliminated)
        row = last_row + 2
        pos = 2
        col_w = (frame_w - 3) // 3 
        pos_col0 = 2
        pos_col1 = pos_col0 + col_w
        pos_col2 = pos_col1 + col_w
        emca48 = A.underline["Player", -A.underline[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos_col0, row)
        terminal.write(text)
        emca48 = A.underline["Eliminated?", -A.underline[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos_col1, row)
        terminal.write(text)
        emca48 = A.underline["Voted For", -A.underline[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos_col2, row)
        terminal.write(text)
        pgi = game.post_game_results
        winner = pgi.winner
        player_cards = pgi.player_cards
        orig_player_cards = pgi.orig_player_cards
        table_cards = pgi.table_cards
        orig_table_cards = pgi.orig_table_cards
        players = player_cards.keys()
        players.sort()
        votes = game.votes
        row += 1
        for player in players:
            terminal.cursorPosition(pos_col0, row)
            if row == th - 2:
                terminal.write("...")
                break
            terminal.write(player)
            terminal.cursorPosition(pos_col1, row)
            elim_flag = " "
            if player in eliminated:
                elim_flag = "Y"
            terminal.write(elim_flag)
            terminal.cursorPosition(pos_col2, row)
            terminal.write(votes.get(player, "N/A"))
            row += 1
        wg = WerewolfGame
        if winner == wg.WINNER_VILLAGE:
            msg = "A Village Victory!"
        elif winner == wg.WINNER_WEREWOLVES:
            msg = "A Werewolf Victory!"
        elif winner == wg.WINNER_TANNER:
            msg = "A Tanner Victory!"
        elif winner == wg.WINNER_TANNER_AND_VILLAGE:
            msg = "A Tanner and Village Victory!"
        elif winner == wg.WINNER_NO_ONE:
            msg = "No One Wins!"
        pos = midway + (frame_w - len(msg)) // 2
        row = equator + 2
        emca48 = A.bold[msg, -A.bold[""]]
        msg = assembleFormattedText(emca48)
        terminal.cursorPosition(pos, row)
        terminal.write(msg)
        player_result_matrix = []
        for player in players:
            entry = (
                player,
                WerewolfGame.get_card_name(orig_player_cards[player]),
                WerewolfGame.get_card_name(player_cards[player]))
            player_result_matrix.append(entry)
        table_result_matrix = zip(
            [WerewolfGame.get_card_name(c) for c in orig_table_cards],
            [WerewolfGame.get_card_name(c) for c in table_cards])
        lines = []
        col_space = 2
        col_w = (frame_w - 3) // 3 
        pos_col0 = midway + 2
        pos_col1 = pos_col0 + col_w
        pos_col2 = pos_col1 + col_w
        row += 2
        emca48 = A.underline["Player", -A.underline[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos_col0, row)
        terminal.write(text)
        emca48 = A.underline["Dealt Card", -A.underline[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos_col1, row)
        terminal.write(text)
        emca48 = A.underline["Final Card", -A.underline[""]]
        text = assembleFormattedText(emca48)
        terminal.cursorPosition(pos_col2, row)
        terminal.write(text)
        row += 1
        for player, dealt, final in player_result_matrix:
            terminal.cursorPosition(pos_col0, row)
            if row == th - 2:
                terminal.write("...")
                break
            terminal.write(player)
            terminal.cursorPosition(pos_col1, row)
            terminal.write(dealt)
            terminal.cursorPosition(pos_col2, row)
            terminal.write(final)
            row += 1
        row += 1
        for n, (dealt, final) in enumerate(table_result_matrix):
            terminal.cursorPosition(pos_col0, row)
            if row >= th - 2:
                terminal.write("...")
                break
            terminal.write("Table {}".format(n + 1))
            terminal.cursorPosition(pos_col1, row)
            terminal.write(dealt)
            terminal.cursorPosition(pos_col2, row)
            terminal.write(final)
            row += 1
        
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
        self._ready_to_advance = True
        self.game.signal_advance(user_id)
        self.update_display()

    def _show_help(self):
        dialog = HelpDialog()
        self.install_dialog(dialog)
        dialog.draw()

    def _show_chat(self):
        input_buf = self.input_buf
        game = self.game
        session_entry = session.get_entry(game.session_id)
        output_buf = session_entry.chat_buf
        dialog = ChatDialog.make_instance(input_buf, output_buf)
        self.install_dialog(dialog)
        self.new_chat_flag = False
        self.update_display()

    def _handle_new_chat_message(self):
        dialog = self.dialog
        if dialog is None:
            self.new_chat_flag = True
            self._draw_player_area()
            self.set_cursor_end_pos()
        else:
            dialog.draw()
            self.set_cursor_end_pos()

    def _show_session_admin(self):
        # Check permission
        game = self.game
        session_entry = session.get_entry(game.session_id)
        owner = session_entry.owner
        if owner == self.user_id:
        # Create dialog.
            dialog = SessionAdminDialog()
            self.install_dialog(dialog)
        else:
            dialog = BriefMessageDialog()
            dialog.brief_message = "Only the session administrator can modify game settings."
            self.install_dialog(dialog)
        dialog.draw()

    def receive_signal(self, signal):
        signame, sigvalue = signal
        if signame == 'next-phase':
            self._handle_next_phase() 
        elif signame == 'chat-message':
            self._handle_new_chat_message() 
        elif signame == 'shutdown':
            initiator = sigvalue['initiator']
            self._start_shutdown(initiator)

    def _start_shutdown(self, initiator):
        parent = self.parent()
        entry = users.get_user_entry(self.user_id)
        entry.app_protocol = None
        if initiator == self.user_id:
            self._shutdown()
        else:
            avatar = self.avatar

            def _make_handler(avatar):

                def _handler():
                    self._shutdown() 

                return _handler

            user_id = self.user_id
            msg = "{} has left the game.".format(initiator)
            dialog = SystemMessageDialog.make_dialog(
                msg,
                on_close=_make_handler(avatar))
            self.install_dialog(dialog)
            self.update_display()

    def _shutdown(self):
        """
        Allow the app to shutdown gracefully.
        """
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        user_entry.joined_id = None
        user_entry.invited_id = None
        session_id = self.game.session_id
        session_entry = session.get_entry(session_id)
        members = session_entry.members
        members.discard(user_id)
        avatar = user_entry.avatar
        avatar.init_app_protocol()


class WebGameProtocol(WebAppBase):
    interface.implements(IWebApplication)

    actions = None
    cards = None
    game = None
    input_buf = None
    new_chat_flag = False
    player_cards = None
    reactor = None
    resource = "werewolves"
    user_id = None
    _ready_to_advance = False
    _shutting_down = False

    @classmethod
    def make_protocol(klass, **kwds):
        instance = klass()
        for k, v in kwds.items():
            if hasattr(instance, k):
                setattr(instance, k, v)
        instance.commands = {}
        entry = users.get_user_entry(instance.user_id)
        session_entry = session.get_entry(entry.joined_id)
        if session_entry.appstate is None or kwds.get('reset', False):
            players = session_entry.members
            game = HandledWerewolfGame()
            session_entry.appstate = game
            game.session_id = session_entry.session_id
            game.add_players(players)
            werewolf_count = kwds.get('werewolves', 2)
            wg = WerewolfGame
            other_roles = kwds.get('roles', set([
                wg.CARD_SEER,
                wg.CARD_ROBBER,
                wg.CARD_TROUBLEMAKER,
                wg.CARD_MINION,
                wg.CARD_INSOMNIAC,
                wg.CARD_HUNTER,
                wg.CARD_TANNER,
            ]))
            instance.reactor.callLater(
                0, game.deal_cards, werewolf_count, other_roles)
        instance.game = session_entry.appstate
        instance.input_buf = []
        return instance

    @property
    def appstate(self):
        """
        Application interface.
        Return the machine that drives the application.
        """
        return self.game

    def request_update(self, key):
        """
        Part of web application interface.
        Update the client based on the key provided.
        """
        if key == 'actions':
            self._update_client_actions()

    def _update_client_actions(self):
        avatar = self.avatar
        actions = self.actions
        command = {'actions': actions}
        command_string = json.dumps(command)
        avatar.send_event_to_client(command_string)

    def _handle_next_phase(self):
        self._ready_to_advance = False
        self._init_phase_elements()
        #self._update_client_phase()
        #self._update_client_output()
        self._update_client_actions()

    def _init_phase_elements(self):
        game = self.game
        phase = game.phase
        if phase == game.PHASE_TWILIGHT:
            self._init_twilight()
        elif phase == game.PHASE_WEREWOLVES:
            pass
        elif phase == game.PHASE_MINION:
            pass
        elif phase == game.PHASE_SEER:
            pass
        elif phase == game.PHASE_ROBBER:
            pass
        elif phase == game.PHASE_TROUBLEMAKER:
            pass
        elif phase == game.PHASE_INSOMNIAC:
            pass
        elif phase == game.PHASE_DAYBREAK:
            pass
        elif phase == game.PHASE_ENDGAME:
            pass

    def _init_twilight(self):
        instructions = ""
        actions = [
            ('Advance Phase', 'Advance to the next phase', 0),
        ]
        self.actions = actions
        self.handlers = {
            0: self._signal_advance,
        }

    def _signal_advance(self):
        """
        Tell the game that this player has signaled it is OK to advance
        to the next phase.
        """
        user_id = self.user_id
        self.game.signal_advance(user_id)
        self._ready_to_advance = True

    def _show_chat(self):
        input_buf = self.input_buf
        game = self.game
        session_entry = session.get_entry(game.session_id)
        output_buf = session_entry.chat_buf
        dialog = ChatDialog.make_instance(input_buf, output_buf)
        self.install_dialog(dialog)
        self.new_chat_flag = False

    def receive_signal(self, signal):
        signame, value = signal
        if signame == 'next-phase':
            self._handle_next_phase()
        elif signame == 'chat-message':
            self._handle_new_chat()
            return
        elif signame == 'shutdown':
            initiator = value['initiator']
            self._shutdown(initiator)

    def _handle_new_chat(self):
        user_entry = users.get_user_entry(self.user_id)
        session_id = user_entry.joined_id
        if session_id is None:
            session_id = user_entry.invited_id
        session_entry = session.get_entry(session_id)
        output_buf = session_entry.chat_buf
        sender, msg = output_buf[-1]
        avatar = user_entry.avatar
        event = {'chat': {'sender': sender, 'message': msg}}
        event_str = json.dumps(event)
        avatar.send_event_to_client(event_str)

    def _shutdown(self, initiator):
        """
        Allow the app to shutdown gracefully.
        """
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        user_entry.joined_id = None
        user_entry.invited_id = None
        session_id = self.game.session_id
        session_entry = session.get_entry(session_id)
        members = session_entry.members
        members.discard(user_id)
        if user_id == initiator:
            return
        msg = "{} has left the game.".format(initiator)
        payload = {}
        if initiator != user_id:
            payload['message'] = msg
        event = { 'shutdown': payload } 
        event_str = json.dumps(event)
        avatar = user_entry.avatar
        avatar.send_event_to_client(event_str)

