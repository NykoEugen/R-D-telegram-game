"""
FSM State Management Service for the Telegram RPG game bot.

This service handles synchronization between FSM states and PostgreSQL GameSession storage.
"""

import json
from typing import Optional, Dict, Any, Union
from datetime import datetime

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import GameSession, SessionStatus
from app.models.player import Player
from app.services.repositories.session_repo import SessionRepository
from app.services.repositories.player_repo import PlayerRepository
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class FSMStateService:
    """Service for managing FSM state synchronization with PostgreSQL."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = SessionRepository(session)
        self.player_repo = PlayerRepository(session)
    
    async def sync_fsm_to_postgres(
        self,
        fsm_context: FSMContext,
        user_id: int,
        action: Optional[str] = None,
        scene_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Optional[GameSession]:
        """
        Sync FSM state data to PostgreSQL GameSession.
        
        Args:
            fsm_context: The FSM context containing current state
            user_id: Telegram user ID
            action: Action that triggered the sync
            scene_id: Current scene ID
            additional_data: Additional data to store
            
        Returns:
            Updated GameSession or None if sync failed
        """
        try:
            # Get current FSM state data
            fsm_data = await fsm_context.get_data()
            current_state = await fsm_context.get_state()
            
            # Get or create player
            player = await self.player_repo.get_player_by_user_id(user_id)
            if not player:
                logger.warning("Player not found for user_id", user_id=user_id)
                return None
            
            # Get or create active game session
            game_session = await self.session_repo.get_active_session(player.id)
            if not game_session:
                # Create new session if none exists
                game_session = await self.session_repo.create_session(
                    player_id=player.id,
                    start_scene_id=scene_id,
                    session_data=fsm_data,
                    client_info={"sync_method": "fsm_to_postgres"}
                )
                logger.info("Created new game session", 
                           session_id=game_session.session_id,
                           player_id=player.id)
            else:
                # Update existing session
                session_data = game_session.session_data or {}
                session_data.update(fsm_data)
                
                # Add action info to session data
                session_data.update({
                    "last_action": action,
                    "last_scene_id": scene_id,
                    "last_sync": datetime.utcnow().isoformat(),
                    **(additional_data or {})
                })
                
                game_session = await self.session_repo.update_session(
                    game_session.session_id,
                    session_data=session_data,
                    current_state=current_state,
                    start_scene_id=scene_id or game_session.start_scene_id
                )
                
                # Increment action counter if action provided
                if action:
                    await self.session_repo.increment_session_counters(
                        game_session.session_id,
                        actions=1
                    )
                
                logger.info("Updated game session", 
                           session_id=game_session.session_id,
                           fsm_state=current_state,
                           action=action)
            
            return game_session
            
        except Exception as e:
            logger.error("Failed to sync FSM to PostgreSQL",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return None
    
    async def restore_fsm_from_postgres(
        self,
        fsm_context: FSMContext,
        user_id: int
    ) -> Optional[GameSession]:
        """
        Restore FSM state from PostgreSQL GameSession.
        
        Args:
            fsm_context: The FSM context to restore state to
            user_id: Telegram user ID
            
        Returns:
            GameSession if restoration was successful, None otherwise
        """
        try:
            # Get player
            player = await self.player_repo.get_player_by_user_id(user_id)
            if not player:
                logger.warning("Player not found for user_id", user_id=user_id)
                return None
            
            # Get active game session
            game_session = await self.session_repo.get_active_session(player.id)
            if not game_session:
                logger.info("No active session found for player", player_id=player.id)
                return None
            
            # Restore FSM state
            session_data = game_session.session_data or {}
            current_fsm_state = game_session.current_state
            
            if current_fsm_state:
                # Set the FSM state
                await fsm_context.set_state(current_fsm_state)
                logger.info("Restored FSM state", 
                           session_id=game_session.session_id,
                           fsm_state=current_fsm_state)
            
            # Restore FSM data (excluding internal fields)
            fsm_data = {k: v for k, v in session_data.items() 
                       if k not in ["last_action", "last_scene_id", "last_sync"]}
            
            if fsm_data:
                await fsm_context.update_data(**fsm_data)
                logger.info("Restored FSM data", 
                           session_id=game_session.session_id,
                           data_keys=list(fsm_data.keys()))
            
            return game_session
            
        except Exception as e:
            logger.error("Failed to restore FSM from PostgreSQL",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return None
    
    async def create_or_get_session(
        self,
        user_id: int,
        scene_id: Optional[str] = None,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> Optional[GameSession]:
        """
        Create a new session or get existing active session.
        
        Args:
            user_id: Telegram user ID
            scene_id: Starting scene ID
            initial_data: Initial session data
            
        Returns:
            GameSession instance
        """
        try:
            # Get or create player
            player = await self.player_repo.get_player_by_user_id(user_id)
            if not player:
                logger.warning("Player not found for user_id", user_id=user_id)
                return None
            
            # Check for existing active session
            game_session = await self.session_repo.get_active_session(player.id)
            if game_session:
                logger.info("Found existing active session", 
                           session_id=game_session.session_id,
                           player_id=player.id)
                return game_session
            
            # Create new session
            game_session = await self.session_repo.create_session(
                player_id=player.id,
                start_scene_id=scene_id,
                session_data=initial_data or {},
                client_info={"created_by": "fsm_service"}
            )
            
            logger.info("Created new game session", 
                       session_id=game_session.session_id,
                       player_id=player.id,
                       scene_id=scene_id)
            
            return game_session
            
        except Exception as e:
            logger.error("Failed to create or get session",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return None
    
    async def end_session(
        self,
        user_id: int,
        status: SessionStatus = SessionStatus.COMPLETED,
        end_scene_id: Optional[str] = None
    ) -> bool:
        """
        End the active session for a user.
        
        Args:
            user_id: Telegram user ID
            status: Final session status
            end_scene_id: Ending scene ID
            
        Returns:
            True if session was ended successfully
        """
        try:
            # Get player
            player = await self.player_repo.get_player_by_user_id(user_id)
            if not player:
                logger.warning("Player not found for user_id", user_id=user_id)
                return False
            
            # Get active session
            game_session = await self.session_repo.get_active_session(player.id)
            if not game_session:
                logger.info("No active session found to end", player_id=player.id)
                return True  # No session to end, consider it successful
            
            # End the session
            await self.session_repo.end_session(
                game_session.session_id,
                status=status,
                end_scene_id=end_scene_id
            )
            
            logger.info("Ended game session", 
                       session_id=game_session.session_id,
                       status=status.value,
                       end_scene_id=end_scene_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to end session",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return False
    
    async def get_session_state(
        self,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get current session state for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Session state data or None if not found
        """
        try:
            # Get player
            player = await self.player_repo.get_player_by_user_id(user_id)
            if not player:
                return None
            
            # Get active session
            game_session = await self.session_repo.get_active_session(player.id)
            if not game_session:
                return None
            
            return {
                "session_id": game_session.session_id,
                "status": game_session.status.value,
                "start_scene_id": game_session.start_scene_id,
                "session_data": game_session.session_data,
                "started_at": game_session.started_at,
                "messages_count": game_session.messages_count,
                "actions_count": game_session.actions_count,
            }
            
        except Exception as e:
            logger.error("Failed to get session state",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return None
