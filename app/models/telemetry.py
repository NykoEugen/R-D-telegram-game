"""
Telemetry and analytics models for the Telegram RPG game bot.

This module defines GameSession, MessageLog, and AIGeneration models for storing game sessions, logs, and AI generations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class SessionStatus(str, Enum):
    """Game session status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ERROR = "error"


class MessageType(str, Enum):
    """Message type enumeration."""
    USER_INPUT = "user_input"
    BOT_RESPONSE = "bot_response"
    SYSTEM_MESSAGE = "system_message"
    ERROR_MESSAGE = "error_message"
    AI_GENERATION = "ai_generation"


class AIGenerationType(str, Enum):
    """AI generation type enumeration."""
    SCENE_DESCRIPTION = "scene_description"
    DIALOGUE = "dialogue"
    QUEST_TEXT = "quest_text"
    ITEM_DESCRIPTION = "item_description"
    ACTION_RESPONSE = "action_response"
    CUSTOM = "custom"


class GameSession(Base):
    """GameSession model representing player game sessions."""
    
    __tablename__ = "game_sessions"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to Player
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    
    # Session identification
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # Session properties
    status: Mapped[SessionStatus] = mapped_column(String(20), default=SessionStatus.ACTIVE, nullable=False)
    start_scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Session data
    session_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    player_state_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Session statistics
    messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_generations_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Session timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Session metadata
    client_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Client/bot version info
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="game_sessions")
    message_logs: Mapped[List["MessageLog"]] = relationship("MessageLog", back_populates="game_session")
    ai_generations: Mapped[List["AIGeneration"]] = relationship("AIGeneration", back_populates="game_session")
    
    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, session_id={self.session_id}, player_id={self.player_id}, status={self.status})>"


class MessageLog(Base):
    """MessageLog model representing all messages in game sessions."""
    
    __tablename__ = "message_logs"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to GameSession
    game_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    
    # Message identification
    message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Telegram message ID
    
    # Message properties
    message_type: Mapped[MessageType] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Message context
    scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Message metadata
    message_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_generation_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ai_generations.id"), nullable=True)
    
    # Message timing
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Message status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    game_session: Mapped["GameSession"] = relationship("GameSession", back_populates="message_logs")
    ai_generation: Mapped[Optional["AIGeneration"]] = relationship("AIGeneration", back_populates="message_logs")
    
    def __repr__(self) -> str:
        return f"<MessageLog(id={self.id}, game_session_id={self.game_session_id}, type={self.message_type})>"


class AIGeneration(Base):
    """AIGeneration model representing AI-generated content."""
    
    __tablename__ = "ai_generations"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to GameSession
    game_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    
    # Generation identification
    generation_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    # Generation properties
    generation_type: Mapped[AIGenerationType] = mapped_column(String(50), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Generation context
    context_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # AI model information
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Generation metrics
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Generation timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Generation status
    is_successful: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Generation quality metrics
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    user_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5 stars
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Generation metadata
    generation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    game_session: Mapped["GameSession"] = relationship("GameSession", back_populates="ai_generations")
    message_logs: Mapped[List["MessageLog"]] = relationship("MessageLog", back_populates="ai_generation")
    
    def __repr__(self) -> str:
        return f"<AIGeneration(id={self.id}, generation_id={self.generation_id}, type={self.generation_type}, successful={self.is_successful})>"
