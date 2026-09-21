"""Concrete games: Undercover, Werewolf, and Avalon."""

from .avalon import Avalon
from .undercover import Undercover, load_word_pairs
from .werewolf import Werewolf

__all__ = ["Avalon", "Undercover", "Werewolf", "load_word_pairs"]
