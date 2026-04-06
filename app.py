import re
import streamlit as st

def process_markdown_final(text):
    if not text:
        return "", ""

    # 1. 인용 표시 지우기
    text = re.sub(r'(?i)[\[【]\s*cite\s*[:\s]*[^\]】]*[\]】]', '', text)

    # 2. 각 키워드별 '진짜 제목 줄' 수집
    target_keywords = [
        "출제자 시점 메인 테마",
        "가독성 개선 강의록",
        "마스터 뼈대 완벽 통합",
        "실전 출제 포인트 & 족보 연동"
    ]

    lines = text.split('\n')
    true_headers = []

    for keyword in target_keywords:
        kw_lines = [line for line in lines if keyword in line]
        if kw_lines:
            shortest_line = min(kw_lines, key=len)
            if shortest_line not in true_headers:
                true_headers.append(shortest_line)

    intro_part = text
    main_part = ""

    # 3. 문서 분리
    if true_headers:
        split_idx = min(text.find(th) for th in true_headers if text.find(th) != -1)
        intro_part = text[:split_idx].strip()
        main_part = text[split_idx:]

    if not main_part:
        return intro_part, ""

    # --- 메인 콘텐츠 전처리 ---
    
    # 4. 가로줄 제거
    main_part = re.sub(r'(?m)^-{3,}\s*$', '', main_part)

    # 5. AI가 빼먹은 글머리기호 강제 줄바꿈
    split_lines = main_part.split('\n')
    fixed_lines = []
    for line in split_lines:
        match = re.match(r'^([ \t]*)', line)
        base_indent = match.group(1) if match else ''
        rep = r'\1\n' + base_indent + '  * '
        line = re.sub(r'([^\s])[ \t]+\*[ \t]+', rep, line)
        fixed_lines.append(line)
    main_part = '\n'.join(fixed_lines)

    # 6. 특수문자만 있는 줄의 경우 다음 줄과 병합
    main_part = re.sub(r'(?m)^([^a-zA-Z0-9가-힣\s]+)\r?\n', r'\1', main_part)

    # 🎯 7. 빈 줄 보존 및 압축 (모두 지우지 않고, 여백 유지를 위해 1줄로 통합)
    main_part = re.sub(r'(?:\r?\n\s*){2,}', '\n\n', main_part.strip())

    # 8. 제목 수준 정규화
    main_lines = main_part.split('\n')
    if main_lines:
        # 최초의 유효한 제목 레벨 찾기 (빈 줄 무시)
        original_first_level = 2
        for line in main_lines:
            if line.strip():
                first_match = re.match(r'^(#{1,5})\s', line)
                if first_match:
                    original_first_level = len(first_match.group(1))
                break
                
        shift = 3 - original_first_level
        clean_true_headers = [th.strip() for th in true_headers]

        for i in range(len(main_lines)):
            current_line = main_lines[i]
            if not current_line.strip():
                continue # 빈 줄은 변환 없이 통과
                
            match = re.match(r'^(#{1,5})\s+(.*)', current_line)
            is_true_header = current_line.strip() in clean_true_headers
            
            if is_true_header:
                content = match.group(2) if match else current_line.lstrip('#').strip()
                main_lines[i] = f"### {content}"
            elif match:
                current_level = len(match.group(1))
                new_level = current_level + shift
                new_level = max(4, min(new_level, 5))
                main_lines[i] = f"{'#' * new_level} {match.group(2)}"

        main_part = '\n'.join(main_lines)

    # 🎯 8.5. 예외 보장: 3단계 바로 뒤에 오는 4단계 사이의 빈 줄은 강제 삭제
    main_part = re.sub(r'(?m)^(###\s+[^\n]*)\n+(####\s+)', r'\1\n\2', main_part)

    # 9. 여백(빈 줄) 지능형 재배치
    main_lines = main_part.split('\n')
    spaced_lines = []
    was_in_list = False
    is_prev_blockquote = False
    last_real_line = "" # 빈 줄을 건너뛰고 구조를 파악하기 위한 기억 장치

    for i, line in enumerate(main_lines):
        stripped = line.lstrip()
        
        # [빈 줄 통과 로직] AI가 의도한 문단 사이의 빈 줄을 그대로 살려줌!
        if not stripped:
            if not spaced_lines or spaced_lines[-1] not in ('', '<br>'):
                spaced_lines.append('')
            was_in_list = False
            is_prev_blockquote = False
            continue

        is_h3 = line.startswith('### ')
        is_h4 = line.startswith('#### ')
        is_blockquote = stripped.startswith('>')
        is_bullet = bool(re.match(r'^([\*\-\+]|\d+\.)\s', stripped))
        is_indented = line.startswith(' ') or line.startswith('\t')
        
        if is_bullet:
            currently_in_list = True
        elif was_in_list and is_indented:
            currently_in_list = True
        else:
            currently_in_list = False

        needs_br_gap = False
        needs_normal_gap = False

        is_prev_h3 = last_real_line.startswith('### ')
        is_prev_h4 = last_real_line.startswith('#### ')

        # [조건 A] 3/4단계 제목 여백 (<br> 삽입)
        if is_h3 or is_h4:
            if not last_real_line:
                needs_br_gap = True
            else:
                if is_h4 and is_prev_h3:
                    pass # 3단계 직후 4단계는 예외 (이미 8.5에서 붙여둠)
                else:
                    needs_br_gap = True

        # [조건 B] 인용구/리스트 경계 보호 (일반 빈 줄 삽입)
        elif last_real_line:
            if is_prev_blockquote and not is_blockquote:
                needs_normal_gap = True
            elif not is_prev_blockquote and is_blockquote:
                if not (is_prev_h3 or is_prev_h4):
                    needs_normal_gap = True
            elif currently_in_list and not was_in_list and not (is_prev_h3 or is_prev_h4):
                needs_normal_gap = True
            elif not currently_in_list and was_in_list:
                needs_normal_gap = True

        # 결정된 여백 타입 삽입 (중복 방지 안전망 포함)
        if needs_br_gap:
            # 이미 윗줄이 순수 빈 줄이라면 그 자리를 활용해 <br> 콤보를 만듦
            if spaced_lines and spaced_lines[-1] == '':
                spaced_lines.append('<br>')
                spaced_lines.append('')
            else:
                spaced_lines.append('')
                spaced_lines.append('<br>')
                spaced_lines.append('')
                
        elif needs_normal_gap:
            if not spaced_lines or spaced_lines[-1] not in ('', '<br>'):
                spaced_lines.append('')

        spaced_lines.append(line)
        
        # 다음 루프를 위해 현재 줄의 상태 저장
        was_in_list = currently_in_list
        is_prev_blockquote = is_blockquote
        last_real_line = line

    # 맨 앞에 쓸데없이 들어간 여백 깔끔하게 제거
    while spaced_lines and spaced_lines[0] in ('', '<br>'):
        spaced_lines.pop(0)

    main_part = '\n'.join(spaced_lines)

    return intro_part, main_part

# --- Streamlit 웹 UI ---
st.set_page_config(page_title="마크다운 전처리기", layout="wide")
st.title("📑 Typora용 마크다운 자동 정규화")

input_text = st.text_area("원본 마크다운을 붙여넣으세요:", height=300)

if input_text:
    intro, main = process_markdown_final(input_text)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📌 도입부 (Intro)")
        st.text_area("Intro Output", value=intro, height=500, label_visibility="collapsed")
    with col2:
        st.subheader("📝 메인 콘텐츠 (Main Content)")
        st.text_area("Main Output", value=main, height=500, label_visibility="collapsed")