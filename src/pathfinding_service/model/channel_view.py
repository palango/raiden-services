from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import ClassVar, Type

import marshmallow
from eth_utils import to_checksum_address
from marshmallow_dataclass import add_schema

from pathfinding_service.constants import DEFAULT_REVEAL_TIMEOUT
from pathfinding_service.exceptions import InvalidPFSFeeUpdate
from raiden.transfer.mediated_transfer.mediation_fee import FeeScheduleState as FeeScheduleRaiden
from raiden.utils.typing import (
    Address,
    Balance,
    ChannelID,
    FeeAmount,
    Nonce,
    PaymentAmount,
    TokenAmount,
    TokenNetworkAddress,
)
from raiden_libs.marshmallow import ChecksumAddress


@dataclass
class FeeSchedule(FeeScheduleRaiden):
    timestamp: datetime = datetime(2000, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def from_raiden(cls, fee_schedule: FeeScheduleRaiden, timestamp: datetime) -> "FeeSchedule":
        kwargs = asdict(fee_schedule)
        kwargs.pop("_penalty_func")
        return FeeSchedule(timestamp=timestamp, **kwargs)


@add_schema
@dataclass
class ChannelView:
    """
    Unidirectional view of a bidirectional channel.
    """

    channel_id: ChannelID
    participant1: Address = field(metadata={"marshmallow_field": ChecksumAddress(required=True)})
    participant2: Address = field(metadata={"marshmallow_field": ChecksumAddress(required=True)})
    settle_timeout: int
    token_network_address: TokenNetworkAddress = field(
        metadata={"marshmallow_field": ChecksumAddress(required=True)}
    )
    capacity: TokenAmount = TokenAmount(0)
    reveal_timeout: int = DEFAULT_REVEAL_TIMEOUT
    update_nonce: Nonce = Nonce(0)
    fee_schedule_sender: FeeSchedule = field(default_factory=FeeSchedule)
    fee_schedule_receiver: FeeSchedule = field(default_factory=FeeSchedule)
    Schema: ClassVar[Type[marshmallow.Schema]]

    def update_capacity(
        self, capacity: TokenAmount, nonce: Nonce = Nonce(0), reveal_timeout: int = None
    ) -> None:
        self.update_nonce = nonce
        self.capacity = capacity
        if reveal_timeout is not None:
            self.reveal_timeout = reveal_timeout

    def fee_sender(self, amount: PaymentAmount) -> FeeAmount:
        """Return the mediation fee for this channel when transferring the given amount"""
        return self.fee_schedule_sender.fee(amount, Balance(self.capacity))

    def fee_receiver(self, amount: PaymentAmount) -> FeeAmount:
        """Return the mediation fee for this channel when receiving the given amount"""
        return self.fee_schedule_receiver.fee(amount, Balance(self.capacity))

    def set_sender_fee_schedule(self, fee_schedule: FeeSchedule) -> None:
        if self.fee_schedule_sender.timestamp >= fee_schedule.timestamp:
            raise InvalidPFSFeeUpdate("Timestamp must increase between fee updates")
        self.fee_schedule_sender = fee_schedule

    def set_receiver_fee_schedule(self, fee_schedule: FeeSchedule) -> None:
        if self.fee_schedule_receiver.timestamp >= fee_schedule.timestamp:
            raise InvalidPFSFeeUpdate("Timestamp must increase between fee updates")
        self.fee_schedule_receiver = fee_schedule

    def __repr__(self) -> str:
        return "<ChannelView cid={} from={} to={} capacity={}>".format(
            self.channel_id,
            to_checksum_address(self.participant1),
            to_checksum_address(self.participant2),
            self.capacity,
        )
