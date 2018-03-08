
from __future__ import print_function
import itertools
import random
import attr
from automat import MethodicalMachine


@attr.attrs
class GameSettings(object):
    roles = attr.attrib()
    werewolves = attr.attrib()


@attr.attrs
class PhaseInfo(object):
    tag = attr.attrib()
    phase = attr.attrib()
    card = attr.attrib()
    name = attr.attrib()
    desc = attr.attrib()


@attr.attrs
class PostGameInfo(object):
    winner = attr.attrib()
    player_cards = attr.attrib()
    orig_player_cards = attr.attrib()
    table_cards = attr.attrib()
    orig_table_cards = attr.attrib()


class WerewolfGame(object):

    CARD_WEREWOLF = 0
    CARD_SEER = 1
    CARD_ROBBER = 2
    CARD_TROUBLEMAKER = 3
    CARD_VILLAGER = 4
    CARD_MINION = 5
    CARD_INSOMNIAC = 6
    CARD_HUNTER = 7
    CARD_TANNER = 8

    _card_names = {
        CARD_WEREWOLF: "werewolf",
        CARD_SEER: "seer",
        CARD_ROBBER: "robber",
        CARD_TROUBLEMAKER: "troublemaker",
        CARD_VILLAGER: "villager",
        CARD_MINION: "minion",
        CARD_INSOMNIAC: "insomniac",
        CARD_HUNTER: "hunter",
        CARD_TANNER: "tanner",
    }

    @classmethod
    def get_card_name(klass, card):
        return klass._card_names[card]

    WINNER_VILLAGE = 0
    WINNER_WEREWOLVES = 1
    WINNER_NO_ONE = 2
    WINNER_TANNER = 3
    WINNER_TANNER_AND_VILLAGE = 4

    # ====================
    # Finite state machine
    # ====================
    _machine = MethodicalMachine()

    # --------------
    # Machine states
    # --------------

    TOKEN_HAVE_PLAYERS = "have_players"
    TOKEN_DONT_HAVE_PLAYERS = "dont_have_players"
    TOKEN_CARDS_DEALT = "cards_dealt"
    TOKEN_WEREWOLF_PHASE = "werewolf_pahse"
    TOKEN_MINION_PHASE = "minion_phase"
    TOKEN_SEER_PHASE = "seer_phase"
    TOKEN_SEER_POWER_ACTIVATED = "seer_power_activated"
    TOKEN_ROBBER_PHASE = "robber_phase"
    TOKEN_ROBBER_POWER_ACTIVATED = "robber_power_activated"
    TOKEN_TROUBLEMAKER_PHASE = "troublemaker_phase"
    TOKEN_TROUBLEMAKER_POWER_ACTIVATED = "troublemaker_power_activated"
    TOKEN_INSOMNIAC_PHASE = "insomniac_phase"
    TOKEN_DAYBREAK = "daybreak"
    TOKEN_ENDGAME = "endgame"

    @_machine.state(serialized=TOKEN_HAVE_PLAYERS)
    def have_players(self):
        """
        The game has players configured.
        """

    @_machine.state(serialized=TOKEN_DONT_HAVE_PLAYERS, initial=True)
    def dont_have_players(self):
        """
        The game doesn't have any players set.
        """

    @_machine.state(serialized=TOKEN_CARDS_DEALT)
    def cards_dealt(self):
        """
        Cards have been dealt to players and the table.
        """

    @_machine.state(serialized=TOKEN_WEREWOLF_PHASE)
    def werewolf_phase(self):
        """
        Werewolves wake up and look for each other.
        """

    @_machine.state(serialized=TOKEN_MINION_PHASE)
    def minion_phase(self):
        """
        The minion wakes up and sees the werewolves, but the werewolves
        don't know who the minion is.
        """

    @_machine.state(serialized=TOKEN_SEER_PHASE)
    def seer_phase(self):
        """
        The seer may look at one player's card or 2 cards from the table.
        """

    @_machine.state(serialized=TOKEN_SEER_POWER_ACTIVATED)
    def seer_power_activated(self):
        """
        The seer's power has been activated.
        """

    @_machine.state(serialized=TOKEN_ROBBER_PHASE)
    def robber_phase(self):
        """
        The robber *may* exchange his card with another player's card.
        The robber does *not* perform the night actions of his new card.
        """

    @_machine.state(serialized=TOKEN_ROBBER_POWER_ACTIVATED)
    def robber_power_activated(self):
        """
        The robber's power has been activated.
        """

    @_machine.state(serialized=TOKEN_TROUBLEMAKER_PHASE)
    def troublemaker_phase(self):
        """
        The troublemaker *may* exchange the cards of 2 players without looking
        at them.
        """

    @_machine.state(serialized=TOKEN_TROUBLEMAKER_POWER_ACTIVATED)
    def troublemaker_power_activated(self):
        """
        The troublemaker's power has been activated.
        """

    @_machine.state(serialized=TOKEN_INSOMNIAC_PHASE)
    def insomniac_phase(self):
        """
        The insomniac wakes up after everyone else to see if her card has
        been changed.
        """

    @_machine.state(serialized=TOKEN_DAYBREAK)
    def daybreak(self):
        """
        Daybreak.
        """

    @_machine.state(serialized=TOKEN_ENDGAME)
    def endgame(self):
        """
        Votes are tallied, the results are revealed.
        """

    # ----------------------------------------------
    # Game-specific information for the night phases
    # ----------------------------------------------
    night_phases = [
        PhaseInfo(
            tag="werewolf",
            phase=werewolf_phase,
            card=CARD_WEREWOLF,
            name="Werewolf Phase",
            desc="Werewolves open their eyes and look for each other."),
        PhaseInfo(
            tag="minion",
            phase=minion_phase,
            card=CARD_MINION,
            name="Minion Phase",
            desc="Minion, wake up and see the werewolves."),
        PhaseInfo(
            tag="seer",
            phase=seer_phase,
            card=CARD_SEER,
            name="Seer Phase",
            desc="The Seer may look at one player's card or 2 cards on the table."),
        PhaseInfo(
            tag="robber",
            phase=robber_phase,
            card=CARD_ROBBER,
            name="Robber Phase",
            desc="The Robber may exchange his card for another player's card and look at it."),
        PhaseInfo(
            tag="troublemaker",
            phase=troublemaker_phase,
            card=CARD_TROUBLEMAKER,
            name="Troublemaker Phase",
            desc="The Troublemaker may exchange 2 other player's cards without looking at them."),
        PhaseInfo(
            tag="insomniac",
            phase=insomniac_phase,
            card=CARD_INSOMNIAC,
            name="Insomniac Phase",
            desc="The Insomniac wakes up after everyone else to see if her card changed."),
    ]
    power_activated_phases = [
        PhaseInfo(
            tag="seer_power_activated",
            phase=seer_power_activated,
            card=None,
            name="Seer Phase",
            desc=None),
        PhaseInfo(
            tag="robber_power_activated",
            phase=robber_power_activated,
            card=None,
            name="Robber Phase",
            desc=None),
        PhaseInfo(
            tag="troublemaker_power_activated",
            phase=troublemaker_power_activated,
            card=None,
            name="Troublemaker Phase",
            desc=None),
    ]

    # --------------
    # Machine inputs
    # --------------

    @_machine.input()
    def add_players(self, players):
        """
        Add the labels for the players.  The order of the players turns is
        encoded in the order of the labels.
        """    

    @_machine.input()
    def deal_cards(self, werewolf_count=2, roles=frozenset([
            CARD_SEER, CARD_ROBBER, CARD_TROUBLEMAKER])):
        """
        Deal the cards to the players and 3 to the table.
        """

    @_machine.input()
    def query_cards(self):
        """
        Query which cards will be used in the game.
        """

    @_machine.input()
    def query_player_cards(self):
        """
        Return a mapping of players to cards.
        """

    @_machine.input()
    def query_table_cards(self):
        """
        Return a list of the table cards.
        """

    @_machine.input()
    def advance_phase(self):
        """
        Advance to the next phase.
        """

    @_machine.input()
    def query_phase(self):
        """
        Return the name of the current phase.
        """

    @_machine.input()
    def is_role_active(self):
        """
        Does is the current role active in the game?
        Returns True/False.
        """

    @_machine.input()
    def is_player_active(self, player):
        """
        Return True if player is active.
        """

    @_machine.input()
    def identify_werewolves(self):
        """
        Return a list of players holding werewolf cards.
        """

    @_machine.input()
    def seer_view_player_card(self, player):
        """
        View a player's card.
        """

    @_machine.input()
    def seer_view_table_cards(self, pos1, pos2):
        """
        Use seer's power to view 2 table cards.
        Valid positions are 0, 1, 2.
        """

    @_machine.input()
    def robber_steal_card(self, player):
        """
        Use robber's power to exchange the robber card for aonther player's
        card.
        """

    @_machine.input()
    def troublemaker_switch_cards(self, player_a, player_b):
        """
        Use the troublemaker's power to switch 2 player's cards.
        """
    @_machine.input()
    def insomniac_view_card(self):
        """
        View the insomniac's current card.
        """

    @_machine.input()
    def query_hunter(self):
        """
        Returns the player who currently holds the hunter card or None if
        no one holds the card.
        """

    @_machine.input()
    def eliminate_players(self, players):
        """
        Eliminate a player (or players) and end the game.
        """

    @_machine.input()
    def query_post_game_results(self):
        """
        Returns a PostGameInfo object.
        """

    #----------------
    # Machine outputs
    #----------------

    @_machine.output()
    def _set_players(self, players):
        """
        The players have been added to the game.  Save them.
        """
        self._players = players

    @_machine.output()
    def _map_cards(self, werewolf_count=2, roles=frozenset([
            CARD_SEER, CARD_ROBBER, CARD_TROUBLEMAKER])):
        """
        Deal a card to each player and 3 to the table.
        """
        players = self._players
        player_count = len(players)
        total_cards = player_count + 3
        deck = []
        deck.extend([self.CARD_WEREWOLF] * werewolf_count)
        role_list = list(roles)
        random.shuffle(role_list)
        deck.extend(role_list)
        additional_cards = total_cards - len(deck)
        if additional_cards > 0:
            deck.extend([self.CARD_VILLAGER] * additional_cards)
        deck = deck[:total_cards]
        random.shuffle(deck)
        player_cards = {}
        for player, card in zip(players, deck):
            player_cards[player] = card
        self._player_cards = player_cards
        self._table_cards = deck[-3:]
        self._new_player_cards = dict(player_cards)
        self._new_table_cards = list(self._table_cards)
        self._active_roles = frozenset(deck)

    @_machine.output()
    def _handle_cards_dealt(self, werewolf_count=2, roles=frozenset([
            CARD_SEER, CARD_ROBBER, CARD_TROUBLEMAKER])):
        self.handle_cards_dealt()

    @_machine.output()
    def _query_cards(self):
        cards = list(self._player_cards.values())
        cards.extend(self._table_cards)
        random.shuffle(cards)
        return cards 

    @_machine.output()
    def _query_player_cards(self):
        return dict(self._player_cards)

    @_machine.output()
    def _query_table_cards(self):
        return list(self._table_cards)

    @_machine.output()
    def _query_phase(self):
        pass

    @_machine.output()
    def _is_role_active(self):
        return self._active_card in self._active_roles

    @_machine.output()
    def _is_player_active(self, player):
        card = self._player_cards[player]
        return (self._active_card == card)

    @_machine.output()
    def _identify_werewolves(self):
        player_cards = self._player_cards
        werewolves = []
        for player, card in player_cards.items():
            if card == self.CARD_WEREWOLF:
                werewolves.append(player)
        return werewolves

    @_machine.output()
    def _seer_view_player_card(self, player):
        return self._player_cards[player]

    @_machine.output()
    def _seer_view_table_cards(self, pos1, pos2):
        assert pos1 in (0, 1, 2), "Position must be 0, 1, or 2."
        assert pos2 in (0, 1, 2), "Position must be 0, 1, or 2."
        table_cards = self._table_cards
        card1 = table_cards[pos1]
        card2 = table_cards[pos2]
        return (card1, card2)

    @_machine.output()
    def _robber_steal_card(self, player):
        robber_player = None
        player_cards = self._player_cards
        for p, card in player_cards.items():
            if card == self.CARD_ROBBER:
                robber_player = p
                break
        player_cards = self._new_player_cards
        stolen_card = player_cards[player]
        player_cards[player] = self.CARD_ROBBER
        player_cards[robber_player] = stolen_card
        return stolen_card

    @_machine.output()
    def _troublemaker_switch_cards(self, player_a, player_b):
        player_cards = self._new_player_cards
        card_a = player_cards[player_a]
        card_b = player_cards[player_b]
        player_cards[player_a] = card_b
        player_cards[player_b] = card_a

    @_machine.output()
    def _insomniac_view_card(self):
        player_cards = self._player_cards
        insomniac_player = None
        for player, card in player_cards.items():
            if card == self.CARD_INSOMNIAC:
                insomniac_player = player
                break
        if insomniac_player is None:
            raise Exception("No player was dealt the insomniac role!")
        new_card = self._new_player_cards[insomniac_player]
        return new_card

    @_machine.output()
    def _query_hunter(self):
        player_cards = self._new_player_cards
        hunter = None
        for player, card  in player_cards.items():
            if card == self.CARD_HUNTER:
                hunter = player
                break
        return hunter
    
    @_machine.output()
    def _eliminate_players(self, players):
        """
        Eliminate a player and end the game.
        """
        eliminated_cards = []
        player_cards = self._new_player_cards
        for player in players:
            card = player_cards[player]
            eliminated_cards.append(card)
        self._eliminated_cards = eliminated_cards

    @_machine.output()
    def _query_post_game_results(self):
        eliminated = set(self._eliminated_cards)
        player_cards = self._new_player_cards.values()
        werewolf_player = self.CARD_WEREWOLF in player_cards
        minion_player = self.CARD_MINION in player_cards
        tanner_win = self.CARD_TANNER in eliminated
        village_win = (
            (self.CARD_WEREWOLF in eliminated)
            or
            ((len(eliminated) == 0) and (not werewolf_player))
        )
        werewolf_win = (
            (werewolf_player and (not self.CARD_WEREWOLF in eliminated))
            or 
            ((not werewolf_player) and minion_player and (not self.CARD_MINION in eliminated) and len(eliminated) > 0)
        ) and (not tanner_win)
        if village_win and tanner_win:
            winner = self.WINNER_TANNER_AND_VILLAGE
        elif village_win:
            winner = self.WINNER_VILLAGE
        elif tanner_win:
            winner = self.WINNER_TANNER
        elif werewolf_win:
            winner = self.WINNER_WEREWOLVES
        else:
            winner = self.WINNER_NO_ONE
        pgi = PostGameInfo(
            winner=winner,
            player_cards=dict(self._new_player_cards),
            orig_player_cards=dict(self._player_cards),
            table_cards=list(self._new_table_cards),
            orig_table_cards=list(self._table_cards))
        return pgi
    
    @_machine.output()
    def _handle_daybreak(self):
        self.handle_daybreak()

    @_machine.output()
    def _handle_endgame(self, players):
        self.handle_endgame()

    # `_set_XXX_phase` output for each night phase.
    for info in night_phases:
      
        def make_func(card, tag): 

            def func(self):
                self._active_card = card
                f = getattr(self, 'handle_{}_phase'.format(tag))
                f()

            return func 

        func = make_func(info.card, info.tag)
        func_name = '_set_{}_phase'.format(info.tag)
        func.__name__ = func_name
        func = _machine.output()(func)
        vars()[func_name] = func
        
    # -----------
    # Transitions
    # -----------

    dont_have_players.upon(
        add_players, 
        enter=have_players, 
        outputs=[_set_players]) 
    have_players.upon(
        deal_cards, 
        enter=cards_dealt, 
        outputs=[_map_cards, _handle_cards_dealt])
    cards_dealt.upon(
        query_player_cards, 
        enter=cards_dealt, 
        outputs=[_query_player_cards],
        collector=lambda x: x[-1])
    cards_dealt.upon(
        query_table_cards, 
        enter=cards_dealt, 
        outputs=[_query_table_cards],
        collector=lambda x: x[-1])
    cards_dealt.upon(
        query_cards, 
        enter=cards_dealt, 
        outputs=[_query_cards],
        collector=lambda x: x[-1])
    cards_dealt.upon(
        advance_phase,
        enter=werewolf_phase,
        outputs=[_set_werewolf_phase])
    werewolf_phase.upon(
        advance_phase,
        enter=minion_phase,
        outputs=[_set_minion_phase])
    minion_phase.upon(
        advance_phase,
        enter=seer_phase,
        outputs=[_set_seer_phase])
    seer_phase.upon(
        advance_phase,
        enter=robber_phase,
        outputs=[_set_robber_phase])
    seer_power_activated.upon(
        advance_phase,
        enter=robber_phase,
        outputs=[_set_robber_phase])
    robber_phase.upon(
        advance_phase,
        enter=troublemaker_phase,
        outputs=[_set_troublemaker_phase])
    robber_power_activated.upon(
        advance_phase,
        enter=troublemaker_phase,
        outputs=[_set_troublemaker_phase])
    troublemaker_phase.upon(
        advance_phase,
        enter=insomniac_phase,
        outputs=[_set_insomniac_phase])
    troublemaker_power_activated.upon(
        advance_phase,
        enter=insomniac_phase,
        outputs=[_set_insomniac_phase])
    insomniac_phase.upon(
        advance_phase,
        enter=daybreak,
        outputs=[_handle_daybreak])
    werewolf_phase.upon(
        identify_werewolves,
        enter=werewolf_phase,
        outputs=[_identify_werewolves],
        collector=lambda x: x[-1])
    minion_phase.upon(
        identify_werewolves,
        enter=minion_phase,
        outputs=[_identify_werewolves],
        collector=lambda x: x[-1])
    seer_phase.upon(
        seer_view_player_card,
        enter=seer_power_activated,
        outputs=[_seer_view_player_card],
        collector=lambda x: x[-1])
    seer_phase.upon(
        seer_view_table_cards,
        enter=seer_power_activated,
        outputs=[_seer_view_table_cards],
        collector=lambda x: x[-1])
    robber_phase.upon(
        robber_steal_card,
        enter=robber_power_activated,
        outputs=[_robber_steal_card],
        collector=lambda x: x[-1])
    troublemaker_phase.upon(
        troublemaker_switch_cards,
        enter=troublemaker_power_activated,
        outputs=[_troublemaker_switch_cards])
    insomniac_phase.upon(
        insomniac_view_card,
        enter=insomniac_phase,
        outputs=[_insomniac_view_card],
        collector=lambda x: x[-1])
    daybreak.upon(
        query_hunter,
        enter=daybreak,
        outputs=[_query_hunter],
        collector=lambda x: x[-1])
    daybreak.upon(
        eliminate_players,
        enter=endgame,
        outputs=[_eliminate_players, _handle_endgame])
    endgame.upon(
        query_post_game_results,
        enter=endgame,
        outputs=[_query_post_game_results],
        collector=lambda x: x[-1])
    # Transitions for `query_phase` input for each game phase.
    for info in night_phases:

        def make_collector(info):
        
            def collector(x):
                return info.name

            return collector

        phase = info.phase
        phase.upon(
            query_phase,
            enter=phase,
            outputs=[_query_phase],
            collector=make_collector(info))
    del make_collector
    daybreak.upon(
        query_phase,
        enter=daybreak,
        outputs=[_query_phase],
        collector=lambda x: "Daybreak")
    # Transitions for `is_role_active` for each night phase.
    for info in night_phases:
        phase = info.phase
        phase.upon(
            is_role_active,
            enter=phase,
            outputs=[_is_role_active],
            collector=lambda x: x[-1])
    # Transitions for `is_player_active` input for each night phase, and
    # power-activated phases.
    for info in itertools.chain(night_phases, power_activated_phases):
        phase = info.phase
        phase.upon(
            is_player_active,
            enter=phase,
            outputs=[_is_player_active],
            collector=lambda x: x[-1])

    # --------------
    # Event handlers
    # --------------

    def handle_cards_dealt(self):
        """
        Called after cards have been dealt.
        """
        pass

    def handle_daybreak(self):
        """
        Called when the daybreak phase has been entered.
        """
        pass

    def handle_endgame(self):
        """
        Called when the endgame phase has been entered.
        """
        pass

    # Create `handle_xxx_phase()` handlers.
    for info in night_phases:
      
        def handler(self):
            pass

        func = handler
        func_name = 'handle_{}_phase'.format(info.tag)
        func.__name__ = func_name
        vars()[func_name] = func

    # ------------------------ 
    # Remove extra class info.
    # ------------------------ 
    del night_phases

