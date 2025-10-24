# class Unit(Base):
#     __tablename__ = "units"
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     unit_movement = Column(String, nullable=False)
#     unit_type = Column(String, nullable=False)
#     enemy_player_unit = Column(String, nullable=False) # it's just to make it easier to sort puzzle
#
# class UnitPath(Base):
#     tabele