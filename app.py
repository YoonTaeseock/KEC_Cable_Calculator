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
    except Exception as e:
        st.error(f"❌ KEC_Table.xlsx 파일을 찾을 수 없습니다: {e}")
        st.stop()

    mccb_list = [15, 20, 30, 40, 50, 60, 75, 100, 125, 150, 175, 200, 225, 250, 300, 400, 500, 600, 
                 700, 800, 900, 1000, 1250, 1600, 2000, 4000, 5000, 6300]
    std_sizes = [1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0, 300.0]
    
    return permit_df, conduit_df, cable_df, motor_df, breaker_df, mccb_list, std_sizes

permit_df, conduit_df, cable_df, motor_df, breaker_df, mccb_list, std_sizes = load_excel_db()

# ==========================================
# 2. 모바일 UI (입력부)
# ==========================================
st.markdown("**⚡ KEC Cable Conduit Calculator**")
st.write("---")

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
            
        # 🌟 UI 업데이트: 기동시간 고정값 드롭다운 및 메이커 선택 추가
        col_m3, col_m4 = st.columns(2)
        with col_m3:
            start_time = st.selectbox("기동 시간 (초)", [4, 6, 10, 15, 20], index=2)
        with col_m4:
            breaker_maker = st.selectbox("차단기 메이커", ["모름", "MetaSol(LS)", "Susol(LS)", "HGM(현대)"])
    else:
        load_kw = st.number_input("부하 용량 (kW)", min_value=0.1, value=15.0, step=1.0)
        start_method = "NONE"
        breaker_maker = "모름"

    col_d, col_v = st.columns(2)
    with col_d:
        distance = st.number_input("부하 거리 (m)", min_value=1, value=30, step=5)
    with col_v:
        v_drop_limit = st.number_input("허용 전압강하율 (%)", min_value=0.5, value=3.0, step=0.5)

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
    if is_motor: start_current = i_load * sf_applied

    applied_current = i_load * 1.1
    sel_breaker = next((at for at in mccb_list if at >= applied_current), mccb_list[-1])
    breaker_note = ""
    min_multiple = 3.0

    # 🌟 로직 업데이트: 동작배율 정밀 매칭 (Maker 및 시간 지정)
    if is_motor:
        # AT 컬럼 동적 탐색 (엑셀 구조 변경 대비)
        at_col_idx = 1
        for c in range(min(5, len(breaker_df.columns))):
            if pd.to_numeric(breaker_df.iloc[:, c], errors='coerce').isin(mccb_list).sum() > 5:
                at_col_idx = c
                break
        
        # 기동시간 컬럼 매핑 (엑셀 이미지 기준)
        time_cols = {4: at_col_idx+1, 6: at_col_idx+2, 10: at_col_idx+3, 15: at_col_idx+4, 20: at_col_idx+5}
        breaker_time_col = time_cols.get(start_time, at_col_idx+3)
        
        # 메이커 병합셀 빈칸 채우기 (Pandas ffill 활용)
        maker_series = breaker_df.iloc[:, 0].ffill().astype(str)
        
        for test_at in mccb_list:
            if test_at < applied_current: continue
            
            b_match_idx = pd.to_numeric(breaker_df.iloc[:, at_col_idx], errors='coerce') == test_at
            b_match = breaker_df[b_match_idx]
            
            if not b_match.empty:
                # 특정 Maker 선택 시 해당 메이커 데이터만 필터링
                if breaker_maker != "모름":
                    search_maker = breaker_maker.split('(')[0] # "MetaSol", "Susol", "HGM" 추출
                    match_makers = maker_series[b_match.index]
                    maker_match = b_match[match_makers.str.contains(search_maker, case=False, na=False)]
                    if not maker_match.empty:
                        b_match = maker_match
                
                # 추출된 목록 중 최소 동작배율 추출 (모름일 경우 전체 중 최소값 자동 적용)
                test_multiple = pd.to_numeric(b_match.iloc[:, breaker_time_col], errors="coerce").min()
            else:
                test_multiple = 3.0
                
            if pd.isna(test_multiple): test_multiple = 3.0
            
            # 기동 방어 로직 검증
            if (test_at * test_multiple) >= start_current:
                sel_breaker = test_at
                min_multiple = test_multiple
                breaker_note = f"(기동 방어: {start_time}초 최저 {min_multiple}배율 검증)"
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

    k_coef = 30.8 if phase == 3 else 35.6
    e_max = v_sys * (v_drop_limit / 100.0)

    req_area_vd = (k_coef * distance * i_load) / (1000 * e_max)
    
    final_size = 0
    final_runs = 1
    req_sq_amp = 0
    req_sq_vd = 0
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

    # 1단계: 1조 포설(1~300SQ)
    for s in std_sizes:
        col_idx, temp_method = get_col_idx_and_method(phase, install_method, s)
        try:
            row_match = permit_df[pd.to_numeric(permit_df.iloc[:, 0], errors='coerce') == s]
            base_amp = float(row_match.iloc[0, col_idx]) if not row_match.empty else 0
        except: base_amp = 0
        
        amp = base_amp * c_factor_total
        v_drop = (k_coef * distance * i_load) / (1000 * s) if s > 0 else float('inf')
        
        if amp >= sel_breaker and req_sq_amp == 0: 
            req_sq_amp = s
            req_sq_base_amp = base_amp 
            req_sq_final_amp = amp
            
        if v_drop <= e_max and req_sq_vd == 0: 
            req_sq_vd = s
            
        if amp >= sel_breaker and v_drop <= e_max:
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
                
                if amp > max_amp_this_run:
                    max_amp_this_run = amp
                    max_sq_this_run = s
                
                if amp >= sel_breaker and v_drop <= e_max:
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
        st.error("❌ 입력된 부하 용량이 너무 커서 300SQ 5조 포설로도 허용전류 또는 전압강하를 만족할 수 없습니다.")
        st.stop()

    final_amp = final_base_amp * final_temp_f * final_group_f * final_runs
    final_v_drop = (k_coef * distance * i_load) / (1000 * final_size * final_runs)
    final_v_drop_percent = (final_v_drop / v_sys) * 100

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

    # 전선관 규격 산출
    area_phase_per_run = phase_single_area * lines_per_run
    total_area_per_run = area_phase_per_run + area_pe_single
    req_pipe_area_per_run = total_area_per_run * 3.0 
    
    copy_conduit_txt = ""

    def get_pipe_info(regex_keyword, for_copy=False):
        db_names = conduit_df.iloc[:, 0].astype(str).str.replace(" ", "").str.upper()
        pipes = conduit_df[db_names.str.contains(regex_keyword, regex=True)].reset_index(drop=True)
        for r in range(len(pipes)):
            try:
                pipe_area = float(pipes.iloc[r, 2])
                if pipe_area >= req_pipe_area_per_run: 
                    ratio = (total_area_per_run / pipe_area) * 100
                    base_str = f"{pipes.iloc[r, 1]}"
                    
                    if for_copy:
                        return f"{base_str} {'× ' + str(final_runs) + '조(관)' if final_runs > 1 else ''}"
                    
                    res_str = f"{base_str} (단면적 {pipe_area:.1f}㎟ / 점유율 {ratio:.1f}%)"
                    if final_runs > 1:
                        res_str += f" × {final_runs}조(관)"
                        
                    if r > 0:
                        prev_area = float(pipes.iloc[r-1, 2])
                        prev_ratio = (total_area_per_run / prev_area) * 100
                        res_str += f"\n ➔ [참고] 한 단계 축소 시 {pipes.iloc[r-1, 1]} (점유율 {prev_ratio:.1f}%)"
                    return res_str
            except: pass
        return "불가"

    if "EF" in install_method: 
        conduit_result = "해당 없음 (트레이 공사)"
        copy_conduit_txt = "해당 없음 (트레이 공사)"
    elif "D1" in install_method: 
        conduit_result = f"지중 ELP관  {get_pipe_info('ELP|파형')} \n\n지중 PE관  {get_pipe_info('PE')} "
        copy_conduit_txt = f"ELP {get_pipe_info('ELP|파형', True)} (또는 PE {get_pipe_info('PE', True)})"
    else: 
        conduit_result = f"CD {get_pipe_info('CD|파상')}\n\nHI {get_pipe_info('HI|경질')}\n\nST {get_pipe_info('ST|스틸|강제|후강')}"
        copy_conduit_txt = f"CD {get_pipe_info('CD|파상', True)} / HI {get_pipe_info('HI|경질', True)} / ST {get_pipe_info('ST|스틸|강제|후강', True)}"

    # ==========================================
    # 4. 결과 출력
    # ==========================================
    st.write("---")
    
    st.markdown("**📋 계산 조건**")
    with st.container(border=True):
        st.write(f"**부하:** {load_kw}kW ({sys_type}) / **거리:** {distance}m / **전압강하율:** {v_drop_limit}%")
        
        if "D1" in install_method:
            env_str = f"**공사방법:** {install_method} / **지중온도계수:** {c_temp_ground} ({temp_ground_label})"
        else:
            env_str = f"**공사방법:** {install_method} / **기중온도계수:** {c_temp_air} ({temp_air_label})"
            if "EF" in install_method: env_str += f" / **트레이보정:** {tray_label}"
        st.write(env_str)
        
        if is_motor:
            maker_label = f" ({breaker_maker})" if breaker_maker != "모름" else ""
            st.write(f"**기동방식:** {start_method} (기동 {start_time}초{maker_label}) / **적용 역률(PF):** {pf} / **효율:** {eff}")
        else:
            st.write(f"**적용 역률(PF):** {pf} / **효율:** {eff}")

    st.markdown("**📊 계산 결과**")
    with st.container(border=True):
        st.write(f"**케이블:** {display_cable_name}")
        st.write(f"**보호도체:** {pe_name}")
        st.write(f"**차단기:** MCCB {poles} {sel_breaker}A")
        st.write(f"**전선관 선정:**")
        if "EF" in install_method: st.info(conduit_result)
        else: st.success(conduit_result)

    st.markdown("**⚙️ 계산 과정**")
    with st.container(border=True):
        step_idx = 1
        
        st.write(f"**{step_idx}. 부하전류:** {load_kw}kW × 1000 / ({v_sys}V × {'√3' if phase==3 else '1'} × 역률{pf} × 효율{eff}) = **{i_load:.1f} A**")
        step_idx += 1
        
        if is_motor:
            st.write(f"**{step_idx}. 기동전류:** {i_load:.1f}A × 기동계수({sf_applied}) = **{start_current:.1f} A**")
            step_idx += 1
        
        st.write(f"**{step_idx}. 차단기 선정:** {i_load:.1f}A × 1.1 여유율 = {applied_current:.1f}A 이상 선정")
        if is_motor:
            maker_text = f"[{breaker_maker}] " if breaker_maker != "모름" else "[최소보수값] "
            st.write(f"ㄴ 기동트립 검증: {start_current:.1f}A / {maker_text}동작배율({min_multiple}) = {(start_current/min_multiple):.1f}A ➔ **최종 {sel_breaker}AT 선정**")
        else:
            st.write(f"ㄴ **최종 {sel_breaker}AT 선정**")
        step_idx += 1

        st.write(f"**{step_idx}. 케이블 굵기 산출 (통합 계단식 탐색)**")
        if is_motor and "Y" in start_method:
            st.info("💡 **Y-△ 기동 방식 감안:** 6가닥이 포설되나 기동/운전용 분할선이므로 KEC 기준 독립된 복수회로 간섭 계수 적용에서 전면 제외합니다. (1조 회로 취급)")
            
        if not parallel_mode:
            st.write(f"ㄴ **① 허용전류 기준:** 차단기 {sel_breaker}A 이상 감당 조건")
            st.write(f" ➔ {req_sq_amp}SQ 허용전류({req_sq_base_amp:.1f}A @{phase_str} {applied_method}) × 온도({final_temp_f}) × 복수회로({final_group_f}) = 적용 {req_sq_final_amp:.1f}A ➔ **{req_sq_amp}SQ 필요**")
            
            st.write(f"ㄴ **② 전압강하 기준:** 단면적 A = ({k_coef} × {distance}m × {i_load:.1f}A) / (1000 × {e_max:.1f}V) = **{req_area_vd:.1f}㎟** ➔ **{req_sq_vd}SQ 이상 필요**")
            
            if req_sq_vd > req_sq_amp:
                st.write(f"ㄴ **③ 최종 선정:** 전압강하율 한도({v_drop_limit}%) 만족을 위해 상향 ➔ **{final_size}SQ 확정**")
            else:
                st.write(f"ㄴ **③ 최종 선정:** 두 조건을 모두 만족하는 **{final_size}SQ 확정**")
                
            st.write(f"ㄴ **[최종 검증]** {final_size}SQ 허용전류({final_base_amp:.1f}A @{phase_str} {applied_method}) × 온도({final_temp_f}) × 복수({final_group_f}) = **적용 허용전류 {final_amp:.1f}A** / 적용 전압강하 {(final_v_drop/v_sys)*100:.1f}%")
        else:
            st.write(f"ㄴ **① 1조 포설 한계 초과:** 300SQ 단일 규격으로 조건 불만족")
            st.write(f"ㄴ **② 동상다조 탐색 (150~300SQ):** 최소 조수부터 순차 탐색")
            for trace in failed_traces:
                st.write(f" ➔ [탈락] {trace} (< {sel_breaker}A)")
            st.write(f" ➔ [통과] {final_runs}조 포설 시 허용전류 및 전압강하 동시 만족")
            st.write(f"ㄴ **③ 최종 선정:** **{final_size}SQ × {final_runs}조 포설 확정**")
            
            st.write(f"ㄴ **[허용전류 검증]** {final_size}SQ 허용전류({final_base_amp:.1f}A @{phase_str} {applied_method}) × 온도({final_temp_f}) × 복수({final_group_f}) × {final_runs}조 = **적용 {final_amp:.1f}A**")
            st.write(f"ㄴ **[전압강하 검증]** e = ({k_coef} × {distance}m × {i_load:.1f}A) / (1000 × {final_size}SQ × {final_runs}조) = **{final_v_drop:.1f}V ➔ 적용 {final_v_drop_percent:.1f}%**")
            
        step_idx += 1

        st.write(f"**{step_idx}. 전선관 규격 산출 (점유율 33.3% 이하 검증)**")
        if final_runs > 1:
            st.write(f"ㄴ **1조(Run) 기준 산출:** 케이블({phase_single_area:.1f}㎟ × {lines_per_run}가닥) + 보호도체({area_pe_single:.1f}㎟) = **1조당 단면적 {total_area_per_run:.1f}㎟**")
            st.write(f"ㄴ **필요 최소 내단면적:** {total_area_per_run:.1f}㎟ × 3 = **{req_pipe_area_per_run:.1f}㎟ 이상 ➔ {final_runs}조(관) 동일 적용**")
        else:
            st.write(f"ㄴ 케이블({phase_single_area:.1f}㎟ × {lines_per_run}가닥) + 보호도체({area_pe_single:.1f}㎟) = **총 케이블 단면적 {total_area_per_run:.1f}㎟**")
            st.write(f"ㄴ **필요 최소 내단면적:** {total_area_per_run:.1f}㎟ × 3 = **{req_pipe_area_per_run:.1f}㎟ 이상**")

    # ==========================================
    # 🌟 전체 내용 공유용 텍스트 생성 로직
    # ==========================================
    st.write("---")
    st.markdown("**📲 전체 결과 공유하기 (카톡/문자)**")
    
    # 1. 입력 조건 요약 조립
    kakao_msg = "[광림전기 KEC 케이블 계산서]\n\n"
    kakao_msg += "📋 [계산 조건]\n"
    kakao_msg += f"- 부하: {load_kw}kW ({sys_type}) / 거리: {distance}m / 허용전압강하율: {v_drop_limit}%\n"
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

    # 2. 선정 결과 조립
    kakao_msg += "📊 [계산 결과]\n"
    kakao_msg += f"- 케이블: {display_cable_name}\n"
    kakao_msg += f"- 보호도체: {pe_name}\n"
    kakao_msg += f"- 차단기: MCCB {poles} {sel_breaker}A\n"
    kakao_msg += f"- 전선관: {copy_conduit_txt}\n\n"

    # 3. 산출 계산 과정 조립
    kakao_msg += "⚙️ [계산 과정]\n"
    step_msg_idx = 1
    kakao_msg += f"{step_msg_idx}. 부하전류: {load_kw}kW × 1000 / ({v_sys}V × {'√3' if phase==3 else '1'} × 역률{pf} × 효율{eff}) = {i_load:.1f} A\n"
    step_msg_idx += 1

    if is_motor:
        kakao_msg += f"{step_msg_idx}. 기동전류: {i_load:.1f}A × 기동계수({sf_applied}) = {start_current:.1f} A\n"
        step_msg_idx += 1

    kakao_msg += f"{step_msg_idx}. 차단기 선정: {i_load:.1f}A × 1.1 여유율 = {applied_current:.1f}A 이상 선정\n"
    if is_motor:
        kakao_msg += f" ㄴ 기동트립 검증: {start_current:.1f}A / 배율({min_multiple}) = {(start_current/min_multiple):.1f}A ➔ 최종 {sel_breaker}AT 선정\n"
    else:
        kakao_msg += f" ㄴ 최종 {sel_breaker}AT 선정\n"
    step_msg_idx += 1

    kakao_msg += f"{step_msg_idx}. 케이블 굵기 산출 (통합 탐색)\n"
    if is_motor and "Y" in start_method:
        kakao_msg += " * Y-△ 기동 방식 감안: 독립된 복수회로 간섭 제외 (1조 취급)\n"

    if not parallel_mode:
        kakao_msg += f" ㄴ ① 허용전류: {req_sq_amp}SQ 필요 ({req_sq_base_amp:.1f}A @{phase_str} {applied_method} × 온도{final_temp_f} × 복수{final_group_f} = {req_sq_final_amp:.1f}A)\n"
        kakao_msg += f" ㄴ ② 전압강하: A = ({k_coef} × {distance}m × {i_load:.1f}A) / (1000 × {e_max:.1f}V) = {req_area_vd:.1f}㎟ ➔ {req_sq_vd}SQ 필요\n"
        kakao_msg += f" ㄴ ③ 최종 선정: {final_size}SQ 확정\n"
        kakao_msg += f" ㄴ [최종 검증] 적용 허용전류 {final_amp:.1f}A / 적용 전압강하 {(final_v_drop/v_sys)*100:.1f}%\n"
    else:
        kakao_msg += " ㄴ ① 1조 포설 한계 초과: 300SQ 단일 규격 조건 불만족\n"
        kakao_msg += " ㄴ ② 동상다조 탐색 (최소 조수부터 순차 탐색)\n"
        for trace in failed_traces:
            kakao_msg += f"   ➔ [탈락] {trace} (< {sel_breaker}A)\n"
        kakao_msg += f"   ➔ [통과] {final_runs}조 포설 시 허용전류/전압강하 동시 만족\n"
        kakao_msg += f" ㄴ ③ 최종 선정: {final_size}SQ × {final_runs}조 포설 확정\n"
        kakao_msg += f" ㄴ [허용전류 검증] {final_size}SQ 기본({final_base_amp:.1f}A) × 온도({final_temp_f}) × 복수({final_group_f}) × {final_runs}조 = 적용 {final_amp:.1f}A\n"
        kakao_msg += f" ㄴ [전압강하 검증] e = ({k_coef} × {distance}m × {i_load:.1f}A) / (1000 × {final_size}SQ × {final_runs}조) = {final_v_drop:.1f}V ➔ 적용 {final_v_drop_percent:.1f}%\n"
    step_msg_idx += 1

    kakao_msg += f"{step_msg_idx}. 전선관 규격 산출 (점유율 33.3% 이하)\n"
    if final_runs > 1:
        kakao_msg += f" ㄴ 1조(Run) 기준 단면적: 케이블({phase_single_area:.1f}㎟ × {lines_per_run}가닥) + 보호도체({area_pe_single:.1f}㎟) = {total_area_per_run:.1f}㎟\n"
        kakao_msg += f" ㄴ 필요 최소 내단면적: {total_area_per_run:.1f}㎟ × 3 = {req_pipe_area_per_run:.1f}㎟ 이상 ➔ {final_runs}조(관) 동일 적용\n"
    else:
        kakao_msg += f" ㄴ 총 케이블 단면적: 케이블({phase_single_area:.1f}㎟ × {lines_per_run}가닥) + 보호도체({area_pe_single:.1f}㎟) = {total_area_per_run:.1f}㎟\n"
        kakao_msg += f" ㄴ 필요 최소 내단면적: {total_area_per_run:.1f}㎟ × 3 = {req_pipe_area_per_run:.1f}㎟ 이상\n"

    st.info("💡 우측 상단의 복사(📋) 버튼을 눌러 전체 산출 근거를 복사하세요.")
    st.code(kakao_msg, language="text")