"""
AI Action Service for handling RUN_AI actions with proper logging.

This module handles AI-powered action generation and logs results to the AIGeneration model.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ai.generation_service import AIGenerationService
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.models.telemetry import AIGeneration, AIGenerationType, GameSession
from app.game.actions import Action
from app.game.scenes import SceneContext

logger = get_logger(__name__)


class AIActionService:
    """Service for handling AI-powered actions with database logging."""
    
    def __init__(self):
        self.generation_service = AIGenerationService()
    
    async def execute_run_ai_action(
        self,
        user_id: int,
        action: Action,
        scene_context: SceneContext,
        db_session: AsyncSession,
        game_session_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Execute a RUN_AI action and log the results to the database.
        
        Args:
            user_id: User ID
            action: The action being executed
            scene_context: Current scene context
            db_session: Database session
            game_session_id: Optional game session ID
            additional_context: Additional context for AI generation
            
        Returns:
            Generated AI response or None if failed
        """
        try:
            # Get user language
            user_language = i18n_service.get_user_language(user_id)
            
            # Generate unique generation ID
            generation_id = f"ai_action_{uuid.uuid4().hex[:12]}"
            
            # Prepare AI generation context
            ai_context = {
                "user_id": user_id,
                "action": action.value,
                "scene_id": scene_context.scene_id,
                "scene_type": scene_context.scene_type.value,
                "scene_description": scene_context.description,
                "user_language": user_language,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if additional_context:
                ai_context.update(additional_context)
            
            # Create AI generation record
            ai_generation = AIGeneration(
                generation_id=generation_id,
                generation_type=AIGenerationType.ACTION_RESPONSE,
                prompt=self._build_ai_prompt(action, scene_context, user_language),
                response="",  # Will be updated after generation
                context_data=ai_context,
                scene_id=scene_context.scene_id,
                action_id=action.value,
                model_name=self.generation_service.DEFAULT_MODEL,
                started_at=datetime.utcnow(),
                is_successful=False  # Will be updated after generation
            )
            
            # Add to database session
            db_session.add(ai_generation)
            await db_session.flush()  # Get the ID
            
            # Generate AI response based on action type
            ai_response = await self._generate_ai_response(
                action, scene_context, user_language, ai_context
            )
            
            if ai_response:
                # Update the AI generation record with successful response
                ai_generation.response = ai_response
                ai_generation.completed_at = datetime.utcnow()
                ai_generation.is_successful = True
                ai_generation.duration_ms = int(
                    (ai_generation.completed_at - ai_generation.started_at).total_seconds() * 1000
                )
                
                # Update game session AI generations count if session exists
                if game_session_id:
                    await self._update_session_ai_count(db_session, game_session_id)
                
                logger.info(
                    "AI action executed successfully",
                    user_id=user_id,
                    action=action.value,
                    scene_id=scene_context.scene_id,
                    generation_id=generation_id,
                    response_length=len(ai_response)
                )
                
                return ai_response
            else:
                # Mark as failed
                ai_generation.completed_at = datetime.utcnow()
                ai_generation.is_successful = False
                ai_generation.error_message = "AI generation failed"
                ai_generation.duration_ms = int(
                    (ai_generation.completed_at - ai_generation.started_at).total_seconds() * 1000
                )
                
                logger.warning(
                    "AI action execution failed",
                    user_id=user_id,
                    action=action.value,
                    scene_id=scene_context.scene_id,
                    generation_id=generation_id
                )
                
                return None
                
        except Exception as e:
            logger.error(
                "Error executing AI action",
                user_id=user_id,
                action=action.value,
                scene_id=scene_context.scene_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            return None
    
    def _build_ai_prompt(
        self, 
        action: Action, 
        scene_context: SceneContext, 
        user_language: str
    ) -> str:
        """Build AI prompt based on action and scene context."""
        action_prompt = i18n_service.get_action_prompt(0, action.value)  # Use 0 as dummy user_id
        
        prompt = f"""
You are a fantasy RPG game master. The player has chosen the action: {action.value}

Scene Context:
- Scene ID: {scene_context.scene_id}
- Scene Type: {scene_context.scene_type.value}
- Description: {scene_context.description}

Action Intent: {action_prompt}

Generate a dynamic, engaging response that:
1. Acknowledges the player's action
2. Describes what happens as a result
3. Advances the story or provides meaningful consequences
4. Maintains the fantasy RPG atmosphere
5. Is appropriate for the current scene context

Keep the response concise (2-3 sentences) and engaging.
Language: {user_language}
"""
        return prompt.strip()
    
    async def _generate_ai_response(
        self,
        action: Action,
        scene_context: SceneContext,
        user_language: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate AI response using the generation service."""
        try:
            # For now, use the existing quest generation method as a template
            # This can be extended to support different types of AI generation
            if action == Action.RUN_AI:
                # Use a custom prompt for RUN_AI actions
                prompt = self._build_ai_prompt(action, scene_context, user_language)
                
                # For now, we'll use the quest generation as a fallback
                # In a full implementation, you'd create a custom AI generation method
                response = await self.generation_service.generate_quest_description(
                    language=user_language
                )
                
                if response:
                    # Customize the response for the action context
                    return f"🤖 **AI Action Result:** {response}"
                else:
                    return "🤖 **AI Action:** The AI is processing your request, but encountered an issue. Please try again."
            else:
                # For other actions, generate contextual responses
                return await self._generate_contextual_response(action, scene_context, user_language)
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            return None
    
    async def _generate_contextual_response(
        self,
        action: Action,
        scene_context: SceneContext,
        user_language: str
    ) -> Optional[str]:
        """Generate contextual response for non-RUN_AI actions."""
        # This is a placeholder for future AI integration with other actions
        # For now, return a simple contextual response
        action_name = i18n_service.get_button_label(0, action.value)  # Use 0 as dummy user_id
        
        if user_language == "uk":
            return f"🎮 **{action_name}:** Ви виконали дію '{action_name}' в сцені '{scene_context.scene_id}'. Результат обробляється..."
        else:
            return f"🎮 **{action_name}:** You performed the action '{action_name}' in scene '{scene_context.scene_id}'. Result is being processed..."
    
    async def _update_session_ai_count(
        self, 
        db_session: AsyncSession, 
        game_session_id: int
    ) -> None:
        """Update the AI generations count for a game session."""
        try:
            result = await db_session.execute(
                select(GameSession).where(GameSession.id == game_session_id)
            )
            session = result.scalar_one_or_none()
            
            if session:
                session.ai_generations_count += 1
                session.updated_at = datetime.utcnow()
                await db_session.flush()
                
        except Exception as e:
            logger.warning(f"Failed to update session AI count: {e}")


# Global instance
ai_action_service = AIActionService()
