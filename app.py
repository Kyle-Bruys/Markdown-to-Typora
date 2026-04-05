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

    # 5. AI가 빼먹은 글머리기호 강제 줄바꿈 (위계 보존)
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

    # 7. 빈 줄 일괄 삭제 (구조 재설계를 위한 초기화)
    main_part = re.sub(r'(?m)^\s*\n', '', main_part)

    # 8. 제목 수준 정규화 (3단계 고정 / 4~5단계 강등)
    main_lines = main_part.split('\n')
    if main_lines:
        first_match = re.match(r'^(#{1,5})\s', main_lines[0])
        original_first_level = len(first_match.group(1)) if first_match else 2
        shift = 3 - original_first_level

        clean_true_headers = [th.strip() for th in true_headers]

        for i in range(len(main_lines)):
            current_line = main_lines[i]
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

        # 🎯 9. 여백(빈 줄) 지능형 재배치 (첫 줄, 3/4단계 예외 완벽 적용)
        spaced_lines = []
        was_in_list = False
        is_prev_blockquote = False

        for i, line in enumerate(main_lines):
            stripped = line.lstrip()
            is_h3 = line.startswith('### ')
            is_h4 = line.startswith('#### ')
            is_blockquote = stripped.startswith('>')
            
            is_bullet = bool(re.match(r'^([\*\-\+]|\d+\.)\s', stripped))
            is_indented = line.startswith(' ') or line.startswith('\t')
            
            if is_bullet:
                currently_in_list = True
            elif was_in_list and is_indented and stripped != '':
                currently_in_list = True
            else:
                currently_in_list = False

            needs_blank_line_br = False  # Typora 제목 강제 여백용 <br>
            needs_blank_line_normal = False  # 일반 마크다운 여백용 \n

            # [조건 A] 3/4단계 제목 처리 (첫 줄 포함)
            if is_h3 or is_h4:
                if i == 0:
                    # 첫 줄이어도 3, 4단계면 무조건 위에 빈 줄(<br>) 추가
                    needs_blank_line_br = True
                else:
                    prev_line = main_lines[i-1]
                    is_prev_h3 = prev_line.startswith('### ')
                    
                    # 💡 예외: 3단계 바로 뒤에 오는 4단계는 빈 줄 안 넣음
                    if is_h4 and is_prev_h3:
                        pass 
                    else:
                        needs_blank_line_br = True
            
            # [조건 B, C] 인용구 및 리스트 보호 처리 (문서 첫 줄이 아닐 때만)
            elif i > 0: 
                prev_line = main_lines[i-1]
                is_prev_h3 = prev_line.startswith('### ')
                is_prev_h4 = prev_line.startswith('#### ')
                
                # 인용구(Blockquote) 탈출/진입 보호
                if is_prev_blockquote and not is_blockquote:
                    needs_blank_line_normal = True 
                elif not is_prev_blockquote and is_blockquote:
                    if not (is_prev_h3 or is_prev_h4):
                        needs_blank_line_normal = True 
                
                # 리스트(List) 블록 보호
                elif currently_in_list and not was_in_list and not (is_prev_h3 or is_prev_h4):
                    needs_blank_line_normal = True 
                elif not currently_in_list and was_in_list and stripped != '':
                    needs_blank_line_normal = True 

            # 결정된 여백 타입에 따라 실제로 리스트에 추가 (중복 방지 안전망)
            if needs_blank_line_br:
                if not spaced_lines or spaced_lines[-1] not in ('', '<br>'):
                    spaced_lines.append('<br>')
            elif needs_blank_line_normal:
                if not spaced_lines or spaced_lines[-1] not in ('', '<br>'):
                    spaced_lines.append('')
            
            # 본문 라인 추가
            spaced_lines.append(line)
            
            # 다음 루프를 위해 상태 업데이트
            was_in_list = currently_in_list
            is_prev_blockquote = is_blockquote

        main_part = '\n'.join(spaced_lines)

    return intro_part, main_part

# --- Streamlit 웹 UI ---
st.set_page_config(page_title="의대생을 위한 MD 전처리기", layout="wide")
st.title("📑 마크다운 자동 정규화 (Typora 완벽 호환)")

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