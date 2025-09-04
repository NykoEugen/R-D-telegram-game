"""
Session repository for the Telegram RPG game bot.

This module provides data access methods for GameSession entities.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.telemetry import GameSession, SessionStatus, MessageLog, MessageType, AIGeneration, AIGenerationType
from app.models.player import Player


class SessionRepository:
    """Repository class for GameSession entity operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_session(
        self,
        player_id: int,
        start_scene_id: Optional[str] = None,
        session_data: Optional[Dict[str, Any]] = None,
        client_info: Optional[Dict[str, Any]] = None
    ) -> GameSession:
        """
        Create a new game session.
        
        Args:
            player_id: The player ID
            start_scene_id: Starting scene ID
            session_data: Additional session data
            client_info: Client/bot version information
            
        Returns:
            GameSession: The created session instance
        """
        session_id = str(uuid.uuid4())
        
        session_data_dict = {
            "player_id": player_id,
            "session_id": session_id,
            "status": SessionStatus.ACTIVE,
            "start_scene_id": start_scene_id,
            "session_data": session_data or {},
            "client_info": client_info,
            "started_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        game_session = GameSession(**session_data_dict)
        self.session.add(game_session)
        await self.session.flush()
        await self.session.refresh(game_session)
        
        return game_session
    
    async def get_session_by_id(self, session_id: int) -> Optional[GameSession]:
        """
        Get a session by its database ID.
        
        Args:
            session_id: The session database ID
            
        Returns:
            GameSession or None if not found
        """
        stmt = select(GameSession).where(GameSession.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_session_by_session_id(self, session_id: str) -> Optional[GameSession]:
        """
        Get a session by its unique session identifier.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            GameSession or None if not found
        """
        stmt = select(GameSession).where(GameSession.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_session(self, player_id: int) -> Optional[GameSession]:
        """
        Get the active session for a player.
        
        Args:
            player_id: The player ID
            
        Returns:
            GameSession or None if no active session
        """
        stmt = (
            select(GameSession)
            .where(
                and_(
                    GameSession.player_id == player_id,
                    GameSession.status == SessionStatus.ACTIVE
                )
            )
            .order_by(desc(GameSession.started_at))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_player_sessions(
        self,
        player_id: int,
        status: Optional[SessionStatus] = None,
        limit: int = 50
    ) -> List[GameSession]:
        """
        Get sessions for a player.
        
        Args:
            player_id: The player ID
            status: Optional status filter
            limit: Maximum number of sessions to return
            
        Returns:
            List of game sessions
        """
        stmt = (
            select(GameSession)
            .where(GameSession.player_id == player_id)
            .order_by(desc(GameSession.started_at))
            .limit(limit)
        )
        
        if status:
            stmt = stmt.where(GameSession.status == status)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_recent_sessions(self, hours: int = 24, limit: int = 100) -> List[GameSession]:
        """
        Get recent sessions within a time period.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of sessions to return
            
        Returns:
            List of recent game sessions
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        stmt = (
            select(GameSession)
            .where(GameSession.started_at >= cutoff_time)
            .order_by(desc(GameSession.started_at))
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_session(
        self,
        session_id: str,
        **updates
    ) -> Optional[GameSession]:
        """
        Update a session's attributes.
        
        Args:
            session_id: The session identifier
            **updates: Dictionary of attributes to update
            
        Returns:
            Updated GameSession or None if not found
        """
        # Add updated_at timestamp
        updates["updated_at"] = datetime.utcnow()
        
        stmt = (
            update(GameSession)
            .where(GameSession.session_id == session_id)
            .values(**updates)
            .returning(GameSession)
        )
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            await self.session.refresh(session)
        
        return session
    
    async def end_session(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED,
        end_scene_id: Optional[str] = None
    ) -> Optional[GameSession]:
        """
        End a game session.
        
        Args:
            session_id: The session identifier
            status: Final session status
            end_scene_id: Ending scene ID
            
        Returns:
            Updated GameSession or None if not found
        """
        session = await self.get_session_by_session_id(session_id)
        if not session:
            return None
        
        # Calculate duration
        duration_seconds = None
        if session.started_at:
            duration = datetime.utcnow() - session.started_at
            duration_seconds = int(duration.total_seconds())
        
        updates = {
            "status": status,
            "end_scene_id": end_scene_id,
            "ended_at": datetime.utcnow(),
            "duration_seconds": duration_seconds,
            "updated_at": datetime.utcnow(),
        }
        
        return await self.update_session(session_id, **updates)
    
    async def save_player_state_snapshot(
        self,
        session_id: str,
        player_state: Dict[str, Any]
    ) -> Optional[GameSession]:
        """
        Save a snapshot of the player's state in the session.
        
        Args:
            session_id: The session identifier
            player_state: Player state data to save
            
        Returns:
            Updated GameSession or None if not found
        """
        return await self.update_session(session_id, player_state_snapshot=player_state)
    
    async def increment_session_counters(
        self,
        session_id: str,
        messages: int = 0,
        actions: int = 0,
        ai_generations: int = 0,
        errors: int = 0
    ) -> Optional[GameSession]:
        """
        Increment session counters.
        
        Args:
            session_id: The session identifier
            messages: Number of messages to add
            actions: Number of actions to add
            ai_generations: Number of AI generations to add
            errors: Number of errors to add
            
        Returns:
            Updated GameSession or None if not found
        """
        session = await self.get_session_by_session_id(session_id)
        if not session:
            return None
        
        updates = {
            "messages_count": session.messages_count + messages,
            "actions_count": session.actions_count + actions,
            "ai_generations_count": session.ai_generations_count + ai_generations,
            "error_count": session.error_count + errors,
            "updated_at": datetime.utcnow(),
        }
        
        return await self.update_session(session_id, **updates)
    
    async def add_message_log(
        self,
        session_id: str,
        message_type: MessageType,
        content: str,
        message_id: Optional[str] = None,
        scene_id: Optional[str] = None,
        action_id: Optional[str] = None,
        message_metadata: Optional[Dict[str, Any]] = None,
        processing_time_ms: Optional[int] = None
    ) -> MessageLog:
        """
        Add a message log to a session.
        
        Args:
            session_id: The session identifier
            message_type: Type of message
            content: Message content
            message_id: Telegram message ID
            scene_id: Scene where message was sent
            action_id: Action that triggered the message
            message_metadata: Additional message metadata
            processing_time_ms: Message processing time in milliseconds
            
        Returns:
            MessageLog: The created message log
        """
        session = await self.get_session_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message_log_data = {
            "game_session_id": session.id,
            "message_id": message_id,
            "message_type": message_type,
            "content": content,
            "scene_id": scene_id,
            "action_id": action_id,
            "message_metadata": message_metadata,
            "processing_time_ms": processing_time_ms,
            "sent_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }
        
        message_log = MessageLog(**message_log_data)
        self.session.add(message_log)
        await self.session.flush()
        await self.session.refresh(message_log)
        
        # Increment message counter
        await self.increment_session_counters(session_id, messages=1)
        
        return message_log
    
    async def add_ai_generation(
        self,
        session_id: str,
        generation_type: AIGenerationType,
        prompt: str,
        response: str,
        generation_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        scene_id: Optional[str] = None,
        action_id: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        duration_ms: Optional[int] = None,
        is_successful: bool = True,
        error_message: Optional[str] = None
    ) -> AIGeneration:
        """
        Add an AI generation record to a session.
        
        Args:
            session_id: The session identifier
            generation_type: Type of AI generation
            prompt: The prompt used
            response: The AI response
            generation_id: Unique generation identifier
            context_data: Additional context data
            scene_id: Scene where generation occurred
            action_id: Action that triggered the generation
            model_name: AI model name
            model_version: AI model version
            temperature: Generation temperature
            max_tokens: Maximum tokens used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens used
            cost_usd: Cost in USD
            duration_ms: Generation duration in milliseconds
            is_successful: Whether generation was successful
            error_message: Error message if generation failed
            
        Returns:
            AIGeneration: The created AI generation record
        """
        session = await self.get_session_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if not generation_id:
            generation_id = str(uuid.uuid4())
        
        ai_generation_data = {
            "game_session_id": session.id,
            "generation_id": generation_id,
            "generation_type": generation_type,
            "prompt": prompt,
            "response": response,
            "context_data": context_data,
            "scene_id": scene_id,
            "action_id": action_id,
            "model_name": model_name,
            "model_version": model_version,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "is_successful": is_successful,
            "error_message": error_message,
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow() if is_successful else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        ai_generation = AIGeneration(**ai_generation_data)
        self.session.add(ai_generation)
        await self.session.flush()
        await self.session.refresh(ai_generation)
        
        # Increment AI generation counter
        await self.increment_session_counters(session_id, ai_generations=1)
        
        return ai_generation
    
    async def get_session_messages(
        self,
        session_id: str,
        message_type: Optional[MessageType] = None,
        limit: int = 100
    ) -> List[MessageLog]:
        """
        Get message logs for a session.
        
        Args:
            session_id: The session identifier
            message_type: Optional message type filter
            limit: Maximum number of messages to return
            
        Returns:
            List of message logs
        """
        session = await self.get_session_by_session_id(session_id)
        if not session:
            return []
        
        stmt = (
            select(MessageLog)
            .where(MessageLog.game_session_id == session.id)
            .order_by(desc(MessageLog.sent_at))
            .limit(limit)
        )
        
        if message_type:
            stmt = stmt.where(MessageLog.message_type == message_type)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_session_ai_generations(
        self,
        session_id: str,
        generation_type: Optional[AIGenerationType] = None,
        limit: int = 100
    ) -> List[AIGeneration]:
        """
        Get AI generation records for a session.
        
        Args:
            session_id: The session identifier
            generation_type: Optional generation type filter
            limit: Maximum number of generations to return
            
        Returns:
            List of AI generation records
        """
        session = await self.get_session_by_session_id(session_id)
        if not session:
            return []
        
        stmt = (
            select(AIGeneration)
            .where(AIGeneration.game_session_id == session.id)
            .order_by(desc(AIGeneration.started_at))
            .limit(limit)
        )
        
        if generation_type:
            stmt = stmt.where(AIGeneration.generation_type == generation_type)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_session_statistics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive statistics for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Dictionary with session statistics or None if session not found
        """
        session = await self.get_session_by_session_id(session_id)
        if not session:
            return None
        
        # Get message counts by type
        message_counts = {}
        for msg_type in MessageType:
            stmt = (
                select(func.count(MessageLog.id))
                .where(
                    and_(
                        MessageLog.game_session_id == session.id,
                        MessageLog.message_type == msg_type
                    )
                )
            )
            result = await self.session.execute(stmt)
            message_counts[msg_type.value] = result.scalar() or 0
        
        # Get AI generation counts by type
        ai_generation_counts = {}
        for gen_type in AIGenerationType:
            stmt = (
                select(func.count(AIGeneration.id))
                .where(
                    and_(
                        AIGeneration.game_session_id == session.id,
                        AIGeneration.generation_type == gen_type
                    )
                )
            )
            result = await self.session.execute(stmt)
            ai_generation_counts[gen_type.value] = result.scalar() or 0
        
        # Calculate total AI cost
        stmt = select(func.sum(AIGeneration.cost_usd)).where(AIGeneration.game_session_id == session.id)
        result = await self.session.execute(stmt)
        total_ai_cost = result.scalar() or 0.0
        
        # Calculate total AI tokens
        stmt = select(func.sum(AIGeneration.total_tokens)).where(AIGeneration.game_session_id == session.id)
        result = await self.session.execute(stmt)
        total_ai_tokens = result.scalar() or 0
        
        return {
            "session_id": session.session_id,
            "player_id": session.player_id,
            "status": session.status.value,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "duration_seconds": session.duration_seconds,
            "start_scene_id": session.start_scene_id,
            "end_scene_id": session.end_scene_id,
            "messages_count": session.messages_count,
            "actions_count": session.actions_count,
            "ai_generations_count": session.ai_generations_count,
            "error_count": session.error_count,
            "message_counts_by_type": message_counts,
            "ai_generation_counts_by_type": ai_generation_counts,
            "total_ai_cost_usd": total_ai_cost,
            "total_ai_tokens": total_ai_tokens,
            "client_info": session.client_info,
        }
    
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Clean up old completed sessions.
        
        Args:
            days: Number of days to keep sessions
            
        Returns:
            Number of sessions deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = delete(GameSession).where(
            and_(
                GameSession.status.in_([SessionStatus.COMPLETED, SessionStatus.ABANDONED]),
                GameSession.ended_at < cutoff_date
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount
