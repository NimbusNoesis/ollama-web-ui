def test_chat_manager_cycle(tmp_path):
    import streamlit as st
    from app.utils.chat_manager import ChatManager

    st.session_state.clear()
    manager = ChatManager(chats_dir=str(tmp_path))

    chat_id = manager.create_new_chat('Test')
    assert chat_id in st.session_state.chats
    manager.add_message('user', 'hi', chat_id)
    assert manager.get_current_chat_title() == 'Test'
    path = tmp_path / f"{chat_id}.json"
    assert path.exists()

    msg_id = manager.prepare_streaming_message(chat_id)
    assert any(m.get('id') == msg_id for m in st.session_state.chats[chat_id]['messages'])
    manager.finalize_streaming_message('done', msg_id, chat_id)
    assert not any(m.get('id') == msg_id and m.get('is_streaming') for m in st.session_state.chats[chat_id]['messages'])

    manager.save_chat(chat_id)
    listed = manager.list_saved_chats()
    assert any(c['id'] == chat_id for c in listed)

    st.session_state.chats.clear()
    manager.load_chat(chat_id)
    assert st.session_state.current_chat_id == chat_id

    manager.delete_chat(chat_id)
    assert chat_id not in st.session_state.chats
    assert not path.exists()

