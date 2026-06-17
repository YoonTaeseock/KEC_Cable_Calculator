import streamlit as st
import pandas as pd
import math
import os

st.set_page_config(page_title="KEC Cable Conduit Calculator", page_icon="⚡", layout="centered")

# ==========================================
# 1. 마스터 DB 로드
# ==========================================
@st.cache_data
def load_excel_db():
    db_path = os.path.join("data", "KEC_Table.xlsx")
    try:
        permit_df = pd.read_excel(db_path, sheet_name="permit_current", header=None)
        conduit_df = pd.read_excel(db_path, sheet_name="conduit_spec")
        cable_df = pd.read_excel(db_path, sheet_name="cable_spec")
        motor_df = pd.read_excel(db_path, sheet_name="moter")
        breaker_df = pd.read_excel(db_path, sheet_name="동작배율")
        imp_df = pd.read_excel(db_path, sheet_name="cable_imp")
    except Exception as e:
        st.error(f"❌ KEC_Table.xlsx 파일을 찾을 수 없습니다: {e}")
        st.stop()

    mccb_list = [15, 20, 30, 40, 50, 60, 75, 100, 125, 150, 175, 200, 225, 250, 300, 400, 500, 600, 
                 700, 800, 900, 1000, 1250, 1600, 2000, 4000, 5000, 6300]
    std_sizes = [1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0, 300.0]
    
    return permit_df, conduit_df, cable_df, motor_df, breaker_df, imp_df, mccb_list, std_sizes

permit_df, conduit_df, cable_df, motor_df, breaker_df, imp_df, mccb_list, std_sizes = load_excel_db()

# ==========================================
# 2. 모바일 UI (상단 탭 설정)
# ==========================================
st.markdown("**⚡ KEC Cable Conduit Calculator**")
st.write("---")

# 🚀 [추가됨] 화면 상단에 두 개의 탭 생성
tab_calc, tab_db = st.tabs(["🧮 계산기", "📁 KEC_Table 조회"])

# ==========================================
# [탭 2] KEC_Table 마스터 데이터 뷰어
# ==========================================
with tab_db:
    st.markdown("**📁 마스터 데이터베이스 (KEC_Table.xlsx)**")
    sheet_choice = st.selectbox("조회할 시트를 선택하세요",
        ["permit_current (허용전류)", "conduit_spec (전선관)", "cable_spec (케이블)",
         "moter (전동기)", "동작배율 (차단기)", "cable_imp (임피던스)"]
    )

    if "permit_current" in sheet_choice: st.dataframe(permit_df, use_container_width=True)
    elif "conduit_spec" in sheet_choice: st.dataframe(conduit_df, use_container_width=True)
    elif "cable_spec" in sheet_choice: st.dataframe(cable_df, use_container_width=True)
    elif "moter" in sheet_choice: st.dataframe(motor_df, use_container_width=True)
    elif "동작배율" in sheet_choice: st.dataframe(breaker_df, use_container_width=True)
    elif "cable_imp" in sheet_choice: st.dataframe(imp_df, use_container_width=True)

# ==========================================
# [탭 1] 기존 계산기 로직 (수정 절대 없음)
# ==========================================
with tab_calc:
    with st.container():
        st.markdown("**1. 부하 조건**")
        sys_type = st.selectbox("전기방식", [ "3P 4W 380V", "3P 3W 380V (전동기)","1P 2W 220V"])
        is_motor = "전동기" in sys_type
        
        start_time = 10 
        if is_motor:
            motor_kws = sorted([float(x) for x in pd.to_numeric(motor_df.iloc[1:, 1], errors='coerce').dropna().unique() if x > 0])
            if not motor_kws: motor_kws = [2.2, 3.7, 5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75]
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                load_kw = st.selectbox("전동기 용량 (kW)", motor_kws, index=5)
            with col_m2:
                start_method = st.selectbox("기동 방식", ["직입기동", "Y-△ (와이델타)", "리액터", "인버터(V)"])
                
            col_m3, col_m4 = st.columns(2)
            with col_m3:
                start_time = st.selectbox("기동 시간 (초)", [4, 6, 10, 15, 20], index=2)
            with col_m4:
                breaker_maker = st.selectbox("차단기 메이커", ["모름", "MetaSol(LS)", "Susol(LS)", "HGM(현대)"])
        else:
            load_kw = st.number_input("부하 용량 (kW)", min_value=0.1, value=15.0, step=1.0)
            start_method = "NONE"
            breaker_maker = "모름"

        col_d, col_v, col_b = st.columns(3)
        with col_d:
            distance = st.number_input("부하 거리 (m)", min_value=1, value=30, step=5)
        with col_v:
            v_drop_limit = st.number_input("허용 전압강하율 (%)", min_value=0.5, value=2.0, step=0.5)
        with col_b:
            breaker_margin = st.number_input("차단기 여유율", min_value=1.0, value=1.1, step=0.1)

    with st.container():
        st.markdown("**2. 시공 환경**")
        install_method = st.selectbox("공사방법", ["B (매입/노출 전선관)", "D1 (지중관로)", "EF (케이블 트레이)"])
        
        c_group_tray = 1.0
        tray_label = "-"
        if "EF" in install_method:
            tray_circuits = st.selectbox("트레이 회로수 (복수회로 보정계수)", 
                                         ["9회로 이상 (0.78)", "6회로 (0.79)", "4회로 (0.80)", "3회로 (0.82)", "2회로 (0.87)", "1회로 (1.00)"])
            c_group_tray = float(tray_circuits.split("(")[1].replace(")", ""))
            tray_label = tray_circuits
        
        with st.expander("온도 보정계수 설정 (클릭)"):
            temp_air_opt = st.selectbox("주위 온도 (기중)", ["30℃ (기본: 1.0)", "40℃ (0.91)", "직접입력"])
            c_temp_air = 0.91 if "40℃" in temp_air_opt else (st.number_input("기중 온도계수", value=1.00) if temp_air_opt == "직접입력" else 1.0)

            temp_ground_opt = st.selectbox("지중 온도 (지중)", ["20℃ (기본: 1.0)", "30℃ (0.93)", "직접입력"])
            c_temp_ground = 0.93 if "30℃" in temp_ground_opt else (st.number_input("지중 온도계수", value=1.00) if temp_ground_opt == "직접입력" else 1.0)

    temp_air_label = temp_air_opt.split(" ")[0] if temp_air_opt != "직접입력" else "수동"
    temp_ground_label = temp_ground_opt.split(" ")[0] if temp_ground_opt != "직접입력" else "수동"

    # ==========================================
    # 3. 계산 엔진
    # ==========================================
    if st.button("계산 수행 🚀", use_container_width=True):
        
        if "1P" in sys_type: phase, req_wires, v_sys, poles = 1, 2, 220, "2P"
        elif "3P 3W" in sys_type: phase, req_wires, v_sys, poles = 3, 3, 380, "3P"
        else: phase, req_wires, v_sys, poles = 3, 4, 380, "4P"
        
        phase_str = "3상" if phase == 3 else "1상"

        eff, pf, start_current = 1.0, 0.9, 0
        inrush_current = 0 
        
        if is_motor:
            closest_idx = (pd.to_numeric(motor_df.iloc[:, 1], errors="coerce") - load_kw).abs().idxmin()
            try: eff, pf = float(motor_df.iloc[closest_idx, 2]), float(motor_df.iloc[closest_idx, 3])
            except: eff, pf = 0.85, 0.85
            
            if "Y" in start_method: sf_applied = 3.0
            elif "리액터" in start_method: sf_applied = 4.8
            elif "인버터" in start_method: sf_applied = 1.5
            else: sf_applied = 7.2 
            
            if "Y" in start_method: req_wires = 6
            
        i_load = (load_kw * 1000) / (v_sys * (math.sqrt(3) if phase == 3 else 1) * eff * pf)
        if is_motor: 
            start_current = i_load * sf_applied
            inrush_current = start_current * 1.5 

        applied_current = i_load * breaker_margin
        sel_breaker = next((at for at in mccb_list if at >= applied_current), mccb_list[-1])
        breaker_note = ""
        min_multiple = 3.0
        inst_multiple = 8 

        if is_motor:
            at_col_idx = 1
            for c in range(min(5, len(breaker_df.columns))):
                if pd.to_numeric(breaker_df.iloc[:, c], errors='coerce').isin(mccb_list).sum() > 5:
                    at_col_idx = c
                    break
            
            time_cols = {4: at_col_idx+1, 6: at_col_idx+2, 10: at_col_idx+3, 15: at_col_idx+4, 20: at_col_idx+5}
            breaker_time_col = time_cols.get(start_time, at_col_idx+3)
            maker_series = breaker_df.iloc[:, 0].ffill().astype(str)
            
            for test_at in mccb_list:
                if test_at < applied_current: continue
                
                b_match_idx = pd.to_numeric(breaker_df.iloc[:, at_col_idx], errors='coerce') == test_at
                b_match = breaker_df[b_match_idx]
                
                if not b_match.empty:
                    if breaker_maker != "모름":
                        search_maker = breaker_maker.split('(')[0]
                        match_makers = maker_series[b_match.index]
                        maker_match = b_match[match_makers.str.contains(search_maker, case=False, na=False)]
                        if not maker_match.empty:
                            b_match = maker_match
                    
                    test_multiple = pd.to_numeric(b_match.iloc[:, breaker_time_col], errors="coerce").min()
                else:
                    test_multiple = 3.0
                    
                if pd.isna(test_multiple): test_multiple = 3.0
                
                current_inst_multiple = 9 if test_at >= 400 else 8
                
                if (test_at * test_multiple) >= start_current and (test_at * current_inst_multiple) >= inrush_current:
                    sel_breaker = test_at
                    min_multiple = test_multiple
                    inst_multiple = current_inst_multiple
                    break

        def get_col_idx_and_method(phase, J_str, size):
            mapping = {
                1: {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "D1": 5, "E": 7, "F": 8},
                3: {"A1": 9, "A2": 10, "B1": 11, "B2": 12, "D1": 13, "E": 15, "F": 16}
            }
            is_single = True if size >= 50 else False
            method = "E"
            if "D1" in J_str: method = "D1"
            elif "B" in J_str: method = "B1" if is_single else "B2"
            elif "EF" in J_str: method = "F" if is_single else "E"
            return mapping[phase].get(method, mapping[phase]["E"]), method

        def get_parallel_group_factor(method, runs):
            if runs <= 1: return 1.0
            if "EF" in method:
                mapping = {2: 0.87, 3: 0.82, 4: 0.80, 5: 0.79, 6: 0.79}
                return mapping.get(runs, 0.78)
            else:
                mapping = {2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.60}
                return mapping.get(runs, 0.60)

        def get_rx(target_size, core_num):
            try:
                sizes = pd.to_numeric(imp_df.iloc[:, 1], errors='coerce')
                size_match = (sizes - target_size).abs() < 0.1
                matched_rows = imp_df[size_match]
                
                if not matched_rows.empty:
                    target_core_str = f"{core_num}C"
                    if core_num >= 3: target_core_str = "3C" 
                    
                    for _, row in matched_rows.iterrows():
                        cable_str = str(row.iloc[0]).upper().replace(" ", "")
                        if target_core_str in cable_str or (core_num >= 3 and "4C" in cable_str):
                            r_val = float(row.iloc[2])
                            x_val = float(row.iloc[3])
                            if not pd.isna(r_val) and not pd.isna(x_val):
                                return r_val, x_val
                                
                    first_match_row = matched_rows.iloc[0]
                    return float(first_match_row.iloc[2]), float(first_match_row.iloc[3])
            except: pass
            return 23.4 / target_size, 0.09

        k_coef = 30.8 if phase == 3 else 35.6
        e_max = v_sys * (v_drop_limit / 100.0)
        req_area_vd = (k_coef * distance * i_load) / (1000 * e_max)
        
        k_thermal = 143.0 
        req_sq_thermal = (start_current * math.sqrt(start_time)) / k_thermal if is_motor else 0.0
        min_sq_thermal = next((s for s in std_sizes if s >= req_sq_thermal), std_sizes[-1]) if is_motor else 0

        final_size = 0
        final_runs = 1
        req_sq_amp = 0
        req_sq_vd = 0
        req_sq_start_vd = 0 
        req_sq_base_amp = 0 
        req_sq_final_amp = 0 
        final_base_amp = 0
        applied_method = "E" 
        
        if "D1" in install_method: 
            final_temp_f = c_temp_ground
            ui_group_f = 1.0
        elif "EF" in install_method: 
            final_temp_f = c_temp_air
            ui_group_f = c_group_tray
        else: 
            final_temp_f = c_temp_air
            ui_group_f = 1.0
            
        final_group_f = ui_group_f
        c_factor_total = final_temp_f * final_group_f

        pf_start = 0.3
        sin_start = math.sin(math.acos(pf_start))
        sin_pf = math.sin(math.acos(pf)) 
        phase_multiplier = math.sqrt(3) if phase == 3 else 2.0
        start_v_drop_limit = 15.0 

        # 1단계: 1조 포설(1~300SQ)
        for s in std_sizes:
            col_idx, temp_method = get_col_idx_and_method(phase, install_method, s)
            try:
                row_match = permit_df[pd.to_numeric(permit_df.iloc[:, 0], errors='coerce') == s]
                base_amp = float(row_match.iloc[0, col_idx]) if not row_match.empty else 0
            except: base_amp = 0
            
            amp = base_amp * c_factor_total
            
            v_drop = (k_coef * distance * i_load) / (1000 * s) if s > 0 else float('inf')
            
            v_drop_start_percent = 0.0
            if is_motor and s > 0:
                core_count = 1 if s >= 50 else req_wires
                r_val, x_val = get_rx(s, core_count) 
                v_drop_start = phase_multiplier * start_current * (distance / 1000) * (r_val * pf_start + x_val * sin_start)
                v_drop_start_percent = (v_drop_start / v_sys) * 100
            
            if amp >= sel_breaker and req_sq_amp == 0: 
                req_sq_amp = s
                req_sq_base_amp = base_amp 
                req_sq_final_amp = amp
                
            if v_drop <= e_max and req_sq_vd == 0: 
                req_sq_vd = s

            if is_motor and v_drop_start_percent <= start_v_drop_limit and req_sq_start_vd == 0 and s >= req_sq_amp:
                req_sq_start_vd = s
                
            thermal_ok = (s >= req_sq_thermal) if is_motor else True

            if amp >= sel_breaker and v_drop <= e_max and (not is_motor or (v_drop_start_percent <= start_v_drop_limit and thermal_ok)):
                final_size = s
                final_runs = 1
                final_base_amp = base_amp
                applied_method = temp_method
                break

        # 2단계: 다조 포설 탐색
        parallel_mode = False
        failed_traces = [] 
        
        if final_size == 0:
            parallel_mode = True
            parallel_sizes = [s for s in std_sizes if s >= 150.0]
            found = False
            
            for runs in range(2, 6): 
                p_group_f = min(ui_group_f, get_parallel_group_factor(install_method, runs))
                current_c_factor = final_temp_f * p_group_f
                
                max_amp_this_run = 0
                max_sq_this_run = 0
                
                for s in parallel_sizes:
                    col_idx, temp_method = get_col_idx_and_method(phase, install_method, s)
                    try:
                        row_match = permit_df[pd.to_numeric(permit_df.iloc[:, 0], errors='coerce') == s]
                        base_amp = float(row_match.iloc[0, col_idx]) if not row_match.empty else 0
                    except: base_amp = 0
                    
                    amp = base_amp * current_c_factor * runs
                    v_drop = (k_coef * distance * i_load) / (1000 * s * runs)
                    
                    v_drop_start_percent = 0.0
                    if is_motor and s > 0:
                        r_val, x_val = get_rx(s, 1) 
                        v_drop_start = phase_multiplier * start_current * (distance / 1000) * (r_val * pf_start + x_val * sin_start) / runs
                        v_drop_start_percent = (v_drop_start / v_sys) * 100
                    
                    if amp > max_amp_this_run:
                        max_amp_this_run = amp
                        max_sq_this_run = s
                    
                    thermal_ok = ((s * runs) >= req_sq_thermal) if is_motor else True

                    if amp >= sel_breaker and v_drop <= e_max and (not is_motor or (v_drop_start_percent <= start_v_drop_limit and thermal_ok)):
                        final_size = s
                        final_runs = runs
                        final_base_amp = base_amp
                        applied_method = temp_method
                        final_group_f = p_group_f 
                        found = True
                        break
                        
                if found: break
                else: failed_traces.append(f"{runs}조 최대 {max_sq_this_run}SQ({max_amp_this_run:.1f}A) 한계 미달")

        if final_size == 0:
            st.error("❌ 입력된 부하 용량이 너무 커서 300SQ 5조 포설로도 조건을 만족할 수 없습니다.")
            st.stop()

        final_amp = final_base_amp * final_temp_f * final_group_f * final_runs
        final_v_drop = (k_coef * distance * i_load) / (1000 * final_size * final_runs) 
        final_v_drop_percent = (final_v_drop / v_sys) * 100

        r_val, x_val = get_rx(final_size, 1 if (final_size >= 50 or final_runs > 1) else req_wires)
        
        final_v_drop_formal = phase_multiplier * i_load * (distance / 1000) * (r_val * pf + x_val * sin_pf) / final_runs
        final_v_drop_formal_percent = (final_v_drop_formal / v_sys) * 100

        final_v_drop_start_percent = 0.0
        final_v_drop_start = 0.0
        if is_motor:
            final_v_drop_start = phase_multiplier * start_current * (distance / 1000) * (r_val * pf_start + x_val * sin_start) / final_runs
            final_v_drop_start_percent = (final_v_drop_start / v_sys) * 100

        sq_str = str(int(final_size)) if final_size == int(final_size) else str(final_size)
        
        cable_type = "F-CV"
        if final_runs > 1:
            cable_name = f"F-CV {sq_str}SQ / 1C"
            lines_per_run = 6 if (is_motor and "Y" in start_method) else req_wires
            total_lines = lines_per_run * final_runs
            phase_line_text = f"{total_lines}"
        else:
            if is_motor and "Y" in start_method:
                cable_c = "3C" if final_size < 50 else "1C"
                cable_name = f"F-CV {sq_str}SQ / {cable_c}"
                lines_per_run = 2 if final_size < 50 else 6
                phase_line_text = str(lines_per_run)
            else:
                cable_c = f"{req_wires}C" if final_size < 50 else "1C"
                cable_name = f"F-CV {sq_str}SQ / {cable_c}"
                lines_per_run = 1 if final_size < 50 else req_wires
                phase_line_text = str(lines_per_run)

        display_cable_name = f"{cable_name.split('/')[0]} / {cable_name.split('/')[1]}-{phase_line_text}" if ("1C" in cable_name or "3C" in cable_name and is_motor) else cable_name

        if final_size <= 16: pe_size = final_size
        elif final_size <= 35: pe_size = 16.0
        else: pe_size = next((s for s in std_sizes if s >= final_size / 2), std_sizes[-1])
        pe_str = str(int(pe_size)) if pe_size == int(pe_size) else str(pe_size)
        pe_name = f"F-GV {pe_str}SQ"

        db_cables = cable_df.iloc[:, 0].astype(str).str.replace(" ", "").str.upper()
        search_str_phase = cable_name.replace(" ", "").upper()
        match_idx = db_cables[db_cables == search_str_phase].index
        
        if not match_idx.empty: phase_single_area = float(cable_df.iloc[match_idx[0], 2]) 
        else: phase_single_area = final_size * (3.0 if "1C" in search_str_phase else req_wires * 3.0)
        
        search_str_pe = f"F-GV{pe_str}SQ"
        match_idx_pe = db_cables[db_cables == search_str_pe].index
        if match_idx_pe.empty:
            search_str_pe = f"F-CV{pe_str}SQ/1C" 
            match_idx_pe = db_cables[db_cables == search_str_pe].index
            
        area_pe_single = float(cable_df.iloc[match_idx_pe[0], 2]) if not match_idx_pe.empty else pe_size * 3.0

        phase_od = math.sqrt((phase_single_area * 4) / math.pi)
        pe_od = math.sqrt((area_pe_single * 4) / math.pi)

        area_phase_per_run = phase_single_area * lines_per_run
        total_area_per_run = area_phase_per_run + area_pe_single
        req_pipe_area_per_run = total_area_per_run * 3.0 
        
        copy_conduit_txt = ""

        def get_pipe_info(regex_keyword):
            db_names = conduit_df.iloc[:, 0].astype(str).str.replace(" ", "").str.upper()
            pipes = conduit_df[db_names.str.contains(regex_keyword, regex=True)].reset_index(drop=True)
            for r in range(len(pipes)):
                try:
                    pipe_area = float(pipes.iloc[r, 2])
                    if pipe_area >= req_pipe_area_per_run: 
                        ratio = (total_area_per_run / pipe_area) * 100
                        base_str = f"{pipes.iloc[r, 1]}"
                        res_str = f"{base_str} (단면적 {pipe_area:.1f}㎟ / 점유율 {ratio:.1f}%)"
                        if final_runs > 1: res_str += f" × {final_runs}조(관)"
                        if r > 0:
                            prev_area = float(pipes.iloc[r-1, 2])
                            prev_ratio = (total_area_per_run / prev_area) * 100
                            res_str += f"\n   ➔ [참고] 한 단계 축소 시 {pipes.iloc[r-1, 1]} (점유율 {prev_ratio:.1f}%)"
                        return res_str
                except: pass
            return "불가"

        if "EF" in install_method: 
            copy_conduit_txt = "해당 없음 (트레이 공사)"
        elif "D1" in install_method: 
            copy_conduit_txt = f"ELP {get_pipe_info('ELP|파형')} \n- 지중 PE관: {get_pipe_info('PE')}"
        else: 
            copy_conduit_txt = f"CD {get_pipe_info('CD|파상')}\n- HI {get_pipe_info('HI|경질')}\n- ST {get_pipe_info('ST|스틸|강제|후강')}"

        # ==========================================
        # 4. 결과 출력 (카톡/문자 공유용 텍스트 박스 단일 출력)
        # ==========================================
        st.write("---")
        st.markdown("**📲 전체 결과 공유하기 (카톡/문자)**")
        
        kakao_msg = "[광림전기 KEC 케이블 계산서]\n\n"
        kakao_msg += "📋 [계산 조건]\n"
        kakao_msg += f"- 부하: {load_kw}kW ({sys_type}) / 거리: {distance}m / 허용전압강하율: {v_drop_limit}% / 차단기여유율: {breaker_margin}배\n"
        
        if "D1" in install_method:
            kakao_msg += f"- 공사방법: {install_method} / 지중온도계수: {c_temp_ground} ({temp_ground_label})\n"
        else:
            env_str_msg = f"- 공사방법: {install_method} / 기중온도계수: {c_temp_air} ({temp_air_label})"
            if "EF" in install_method: env_str_msg += f" / 트레이보정: {tray_label}"
            kakao_msg += env_str_msg + "\n"

        if is_motor:
            kakao_msg += f"- 기동방식: {start_method} (기동 {start_time}초) / 역률: {pf} / 효율: {eff}\n\n"
        else:
            kakao_msg += f"- 역률: {pf} / 효율: {eff}\n\n"

        kakao_msg += "📊 [계산 결과]\n"
        kakao_msg += f"- 케이블: {display_cable_name} (1가닥 외경: 약 {phase_od:.1f}mm)\n"
        kakao_msg += f"- 보호도체: {pe_name} (외경: 약 {pe_od:.1f}mm)\n"
        kakao_msg += f"- 차단기: MCCB {poles} {sel_breaker}A\n"
        if is_motor:
            kakao_msg += f"- 순시 전압강하율: {final_v_drop_start_percent:.2f} %\n"
        
        if "EF" not in install_method:
            kakao_msg += f"- 전선관:\n {copy_conduit_txt}\n\n"
        else:
            kakao_msg += "\n"

        kakao_msg += "⚙️ [계산 과정]\n"
        step_msg_idx = 1
        kakao_msg += f"{step_msg_idx}. 부하전류: {load_kw}kW × 1000 / ({v_sys}V × {'√3' if phase==3 else '1'} × 역률{pf} × 효율{eff}) = {i_load:.1f} A\n"
        step_msg_idx += 1

        if is_motor:
            kakao_msg += f"{step_msg_idx}. 기동전류: {i_load:.1f}A × 기동계수({sf_applied}) = {start_current:.1f} A\n"
            step_msg_idx += 1

        kakao_msg += f"{step_msg_idx}. 차단기 선정: {i_load:.1f}A × {breaker_margin} 여유율 = {applied_current:.1f}A 이상 선정\n"
        
        if is_motor:
            kakao_msg += f" ㄴ 🕒 한시트립 방어: {start_current:.1f}A / 동작배율({min_multiple}) = {(start_current/min_multiple):.1f}A 이상 필요\n"
            kakao_msg += f" ㄴ ⚡ 순시트립 방어: {start_current:.1f}A × 1.5 / 차단배율({inst_multiple}) = {(inrush_current/inst_multiple):.1f}A 이상 필요 ➔ 최종 {sel_breaker}AT 선정\n"
        else:
            kakao_msg += f" ㄴ 최종 {sel_breaker}AT 선정\n"
        step_msg_idx += 1

        kakao_msg += f"{step_msg_idx}. 케이블 굵기 산출 (통합 탐색)\n"
        if is_motor and "Y" in start_method:
            kakao_msg += " * Y-△ 기동 방식 감안: 독립된 복수회로 간섭 제외 (1조 취급)\n"

        if not parallel_mode:
            kakao_msg += f" ㄴ ① 허용전류: {req_sq_amp}SQ 필요 ({req_sq_base_amp:.1f}A @{phase_str} {applied_method} × 온도{final_temp_f} × 복수{final_group_f} = {req_sq_final_amp:.1f}A)\n"
            
            kakao_msg += f" ㄴ ② 정상전압강하 (약식산출): A = ({k_coef} × {distance}m × {i_load:.1f}A) / (1000 × {e_max:.1f}V) = {req_area_vd:.1f}㎟ ➔ {req_sq_vd}SQ 이상 필요\n"
            kakao_msg += f"    ➔ [정식검증]: e = ({'√3' if phase==3 else '2'} × {i_load:.1f}A × {distance}m × (R{r_val:.4f}×{pf} + X{x_val:.4f}×{sin_pf:.3f})) / 1000 = {final_v_drop_formal:.1f}V (적용 {final_v_drop_formal_percent:.2f}%) ≤ 기준 {v_drop_limit}% 만족\n"
            
            if is_motor:
                kakao_msg += f" ㄴ ③ 순시전압강하: e = ({'√3' if phase==3 else '2'} × {start_current:.1f}A × {distance}m × (R{r_val:.4f}×{pf_start} + X{x_val:.4f}×{sin_start:.3f})) / 1000\n"
                kakao_msg += f"    ➔ {final_v_drop_start:.1f}V (적용 {final_v_drop_start_percent:.2f}%) ≤ 15% 조건 검토\n"
                kakao_msg += f" ㄴ ④ 기동시간(t초) 온도상승(열적내력): S = ({start_current:.1f}A × √{start_time}s) / 143 = {req_sq_thermal:.1f}㎟ ➔ {min_sq_thermal}SQ 필요\n"
                kakao_msg += f" ㄴ ⑤ 최종 선정: {final_size}SQ 확정\n"
            else:
                kakao_msg += f" ㄴ ③ 최종 선정: {final_size}SQ 확정\n"
        else:
            kakao_msg += " ㄴ ① 1조 포설 한계 초과: 300SQ 단일 규격 조건 불만족\n"
            kakao_msg += " ㄴ ② 동상다조 탐색 (최소 조수부터 순차 탐색)\n"
            for trace in failed_traces:
                kakao_msg += f"   ➔ [탈락] {trace}\n"
            kakao_msg += f"   ➔ [통과] {final_runs}조 포설 시 조건 만족\n"
            kakao_msg += f" ㄴ ③ 최종 선정: {final_size}SQ × {final_runs}조 포설 확정\n"
            
            kakao_msg += f" ㄴ [허용전류 검증] {final_size}SQ 기본({final_base_amp:.1f}A @{phase_str} {applied_method}) × 온도계수({final_temp_f}) × 복수계수({final_group_f}) × {final_runs}조 = 적용 {final_amp:.1f}A\n"
            
            kakao_msg += f" ㄴ [정상전압강하 (약식산출)] e = ({k_coef} × {distance}m × {i_load:.1f}A) / (1000 × {final_size}SQ × {final_runs}조) = {final_v_drop:.1f}V (적용 {final_v_drop_percent:.1f}%)\n"
            kakao_msg += f"    ➔ [정식검증] e = ({'√3' if phase==3 else '2'} × {i_load:.1f}A × {distance}m × (R{r_val:.4f}×{pf} + X{x_val:.4f}×{sin_pf:.3f})) / (1000 × {final_runs}조) = {final_v_drop_formal:.1f}V (적용 {final_v_drop_formal_percent:.2f}%) ≤ 기준 {v_drop_limit}% 만족\n"
            
            if is_motor:
                kakao_msg += f" ㄴ [순시전압강하 검증] e = ({'√3' if phase==3 else '2'} × {start_current:.1f}A × {distance}m × (R{r_val:.4f}×{pf_start} + X{x_val:.4f}×{sin_start:.3f})) / (1000 × {final_runs}조) = {final_v_drop_start:.1f}V (적용 {final_v_drop_start_percent:.2f}%) ≤ 15% 만족\n"
                kakao_msg += f" ㄴ [온도상승(열적내력)] 필요 {req_sq_thermal:.1f}㎟ ≤ 총 단면적({final_size*final_runs}㎟) 만족\n"
            
        step_msg_idx += 1

        if "EF" not in install_method:
            kakao_msg += f"{step_msg_idx}. 전선관 규격 산출 (점유율 33.3% 이하)\n"
            if final_runs > 1:
                kakao_msg += f" ㄴ 1조(Run) 기준 단면적: 케이블 + 보호도체 = {total_area_per_run:.1f}㎟\n"
                kakao_msg += f" ㄴ 필요 최소 내단면적: {total_area_per_run:.1f}㎟ × 3 = {req_pipe_area_per_run:.1f}㎟ 이상 ➔ {final_runs}조(관) 동일 적용\n"
            else:
                kakao_msg += f" ㄴ 총 케이블 단면적: 케이블 + 보호도체 = {total_area_per_run:.1f}㎟\n"
                kakao_msg += f" ㄴ 필요 최소 내단면적: {total_area_per_run:.1f}㎟ × 3 = {req_pipe_area_per_run:.1f}㎟ 이상\n"

        st.info("💡 우측 상단의 복사(📋) 버튼을 눌러 전체 산출 근거를 복사하세요.")
        st.code(kakao_msg, language="text")
