import pandas as pd
import pytest

from src.data_loader import load_test_wishes, load_tours
from src.dialogue import Conversation, ConversationState


@pytest.fixture(scope="session")
def tours() -> pd.DataFrame:
    return load_tours()


@pytest.fixture(scope="session")
def wishes(tours) -> pd.DataFrame:
    return load_test_wishes(tours=tours)


@pytest.fixture(scope="session")
def bot(tours) -> Conversation:
    return Conversation(tours)


@pytest.fixture
def state() -> ConversationState:
    return ConversationState()
