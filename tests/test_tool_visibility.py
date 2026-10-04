from integration import tools, policy


def test_initial_candidate_does_not_reveal_selected_tests(tmp_path, monkeypatch):
    import science.screen
    monkeypatch.setattr(tools,"LIVE",tmp_path)
    monkeypatch.setattr(policy,"DB_PATH",tmp_path/'policy.sqlite3')
    monkeypatch.setattr(policy,"source_digest",lambda: 'a'*64)
    run_id=policy.create_run('UBA3',source_sha256='a'*64)['id']
    monkeypatch.setattr(science.screen,"run_tool",lambda *a,**k: {"status":"computed", "input_hashes":{"countmatrix.xlsx":'a'*64}, "observations":{"gene":"UBA3", "conditions":{"without_il6":{"score":4.1,"repeat_scores":[4,4.2],"leave_one_out":{"score_min":-0.05},"fixed_checklist_pass":False}},"context":{"contrast":1},"guides":["hidden"]}})
    result=tools.analyze("candidate","UBA3",run_id)
    assert "context" not in result["observations"]
    assert "guides" not in result["observations"]
    assert "leave_one_out" not in result["observations"]["conditions"]["without_il6"]
    assert result["observations"]["conditions"]["without_il6"]["score"]==4.1
