#!/usr/bin/env python3
"""
Test script for FSM state management integration.

This script tests the FSM state synchronization with PostgreSQL.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.db import get_async_session
from app.services.fsm_service import FSMStateService
from app.game.states import GameStates
from app.models.telemetry import SessionStatus
from app.services.logging_service import setup_logging, get_logger


async def test_fsm_integration():
    """Test FSM state management integration."""
    
    # Setup logging
    setup_logging(log_level="INFO", enable_console=True)
    logger = get_logger(__name__)
    
    logger.info("🧪 Starting FSM integration test...")
    
    # Test user ID (fake for testing)
    test_user_id = 12345
    
    try:
        async with get_async_session() as session:
            fsm_service = FSMStateService(session)
            
            # Test 1: Create a new session
            logger.info("📝 Test 1: Creating new session...")
            game_session = await fsm_service.create_or_get_session(
                user_id=test_user_id,
                scene_id="test_scene",
                initial_data={"test": "data"}
            )
            
            if game_session:
                logger.info(f"✅ Session created: {game_session.session_id}")
            else:
                logger.error("❌ Failed to create session")
                return False
            
            # Test 2: Simulate FSM state sync
            logger.info("📝 Test 2: Testing FSM state sync...")
            
            # Create a mock FSM context (simplified)
            class MockFSMContext:
                def __init__(self):
                    self.state = None
                    self.data = {}
                
                async def get_state(self):
                    return self.state
                
                async def set_state(self, state):
                    self.state = state
                
                async def get_data(self):
                    return self.data
                
                async def update_data(self, **kwargs):
                    self.data.update(kwargs)
            
            mock_fsm = MockFSMContext()
            await mock_fsm.set_state(GameStates.QUEST_ACTIVE)
            await mock_fsm.update_data(
                quest_description="Test quest",
                scene_id="quest_scene",
                action_count=1
            )
            
            # Sync FSM state to PostgreSQL
            synced_session = await fsm_service.sync_fsm_to_postgres(
                mock_fsm,
                test_user_id,
                action="test_action",
                scene_id="quest_scene",
                additional_data={"test_sync": True}
            )
            
            if synced_session:
                logger.info(f"✅ FSM state synced: {synced_session.current_state}")
                logger.info(f"📊 Session data: {synced_session.session_data}")
            else:
                logger.error("❌ Failed to sync FSM state")
                return False
            
            # Test 3: Test FSM state restoration
            logger.info("📝 Test 3: Testing FSM state restoration...")
            
            # Create a new mock FSM context for restoration
            mock_fsm_restore = MockFSMContext()
            
            # Restore FSM state from PostgreSQL
            restored_session = await fsm_service.restore_fsm_from_postgres(
                mock_fsm_restore,
                test_user_id
            )
            
            if restored_session:
                logger.info(f"✅ FSM state restored: {restored_session.current_state}")
                logger.info(f"📊 Restored data: {mock_fsm_restore.data}")
            else:
                logger.error("❌ Failed to restore FSM state")
                return False
            
            # Test 4: Test session state retrieval
            logger.info("📝 Test 4: Testing session state retrieval...")
            
            session_state = await fsm_service.get_session_state(test_user_id)
            if session_state:
                logger.info(f"✅ Session state retrieved: {session_state['session_id']}")
                logger.info(f"📊 Actions count: {session_state['actions_count']}")
            else:
                logger.error("❌ Failed to retrieve session state")
                return False
            
            # Test 5: Test session ending
            logger.info("📝 Test 5: Testing session ending...")
            
            ended = await fsm_service.end_session(
                test_user_id,
                status=SessionStatus.COMPLETED,
                end_scene_id="end_scene"
            )
            
            if ended:
                logger.info("✅ Session ended successfully")
            else:
                logger.error("❌ Failed to end session")
                return False
            
            logger.info("🎉 All FSM integration tests passed!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


async def main():
    """Main test function."""
    success = await test_fsm_integration()
    
    if success:
        print("\n✅ FSM Integration Test: PASSED")
        sys.exit(0)
    else:
        print("\n❌ FSM Integration Test: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
