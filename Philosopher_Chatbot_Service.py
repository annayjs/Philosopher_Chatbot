import openai
import streamlit as st
import re
import deepl
import os 
from dotenv import load_dotenv
import pandas as pd
import numpy as np
# .env 파일 불러오기
load_dotenv()

# OpenAI API 키 설정
os.environ["OPEN_API_KEY"] = st.secrets["OPENAI_API_KEY"]
openai.api_key = os.environ["OPEN_API_KEY"]

#DeepL API 키 설정
translator = deepl.Translator(os.getenv("DeepL_API_KEY"))

# 사용 가능한 철학자와 대화 프롬프트 목록
philosophers =["니체", '칸트', '맹자', '노자']
#칸트": "In the manner of and with the ideas of Kant, ",
    #"맹자": "In the manner of and with the ideas of Mencius, ",
    #"노자": "In the manner of and with the ideas of Lao Tzu, "

# 답변 길이 목록
len_select = {"짧은 답변 📑": 100, "긴 답변 📜": 300}

#사용가능 모델 목록
available_models = {
    "GPT-3.5-Turbo": "gpt-3.5-turbo",
    "GPT-4": "gpt-4"
}

#Text Embedding 데이터 불러오기
data_url='https://drive.google.com/file/d/1HC8WBybCVfhPN1Tr4a8eKA418azI_d3M/view?usp=sharing'
data_url='https://drive.google.com/uc?id=' + data_url.split('/')[-2]
df = pd.read_pickle(data_url)
df.reset_index(inplace=True)
df.rename(columns={'index': 'philosopher'}, inplace=True)

#sentence transformer
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

#코사인 유사도 구하기
import torch
import torch.nn.functional as F

def cosine_similarity(tensor1, tensor2):
    # 두 텐서 간의 코사인 유사도를 계산합니다.
    return F.cosine_similarity(tensor1, tensor2).item()

def print_similarity(question: str, philosopher: str, doc=df):

    # 허용된 경제 사상의 목록
    allowed_thoughts = {'니체','칸트','소크라테스', '공자', '노자'}

    # 입력된 경제 사상이 허용된 목록에 속하지 않으면 오류 메시지를 반환
    if philosopher not in allowed_thoughts:
        raise ValueError("""
        불가능한 철학자입니다.
        '니체', '칸트', '소크라테스' '공자' '노자' 중 선택하세요.
        """)

    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # 주어진 질문에 대한 임베딩을 계산합니다.
    question_embedding = model.encode(question, convert_to_tensor=True).unsqueeze(0)

    # 사상에 맞는 텍스트 임베딩을 스택합니다.
    doc2 = doc[doc['philosopher'] == philosopher]
    all_embeddings = torch.stack(doc2['embedding'].tolist())

    # 각 문서의 임베딩과 질문의 임베딩 간의 유사도를 계산합니다.
    similarities = F.cosine_similarity(question_embedding, all_embeddings, dim=1)

    # 유사도를 기준으로 상위 3개의 인덱스를 가져옵니다.
    top_indices = similarities.argsort(descending=True)[:3]

    # 상위 3개의 문서를 반환합니다.
    return doc2.iloc[top_indices]['paragraph']

# Streamlit 앱 설정
st.title('🧔📚 철학자와 대화하기')

# 컬럼 생성하여 나란히 배열
col1, col2, col3 = st.columns(3)


# 첫 번째 컬럼에 철학자 선택
# 사용자 선택에 따라 프롬프트 설정
with col1:
    selected_philosopher = st.radio("👨‍🏫 철학자 선택:", philosophers)
chosen_philosopher=selected_philosopher

# 두 번째 컬럼에 답변 길이 선택
# 답변 길이 설정 버튼
# 답변 길이에 따라 max_tokens 설정
with col2:
    selected_len = st.radio("🗣️ 답변 길이:", list(len_select.keys()))
max_tokens = len_select[selected_len]

# 세 번째 컬럼에 모델 선택
#사용할 모델 선택
with col3:
    selected_model = st.radio("🤖 사용할 모델:", list(available_models.keys()))
selected_model_final = available_models[selected_model]


# session_state에 messages 리스트 초기화
if "messages" not in st.session_state:
    system_message="너는 %s야. AI챗봇처럼 대답하지말고, %s가 말하는 것처럼 대답해줘"%(chosen_philosopher, chosen_philosopher)
    system_message_eng=translator.translate_text(system_message, target_lang="EN-US").text
    st.session_state.messages = [
        {"role": "system", 
         "content": system_message_eng}
    ]
    
# 폼 생성
with st.form(key='message_form'):
    # 사용자의 메시지 입력 받기
    st.write("안녕하세요! 환영합니다. 철학자와 대화를 시작해 보세요!")
    user_message = st.text_input("철학자에게 고민을 말해보세요: ")
    
    # 폼 제출 버튼 추가
    submit_button = st.form_submit_button(label='전송')

if submit_button and user_message:
    #user_message_en=translator.translate_text(user_message, target_lang="EN-US").text
    input_eng=translator.translate_text(user_message, target_lang="KO").text
    input_text=print_similarity(input_eng, chosen_philosopher, doc=df)
    user_prompt="""
        상담 내용: %s
        아래에는 %s이 쓴 저서의 구절이야.
            1. ({%s}
            2. {%s}
            3. {%s})
        위 상담 내용에 대해, 위 구절과 %s의 사상을 바탕으로 %d자 이내로, %s의 말투를 사용해서 마치 %s가 말하듯이 친절하게 상담해줘.
        """%(user_message, chosen_philosopher, input_text.iloc[0], input_text.iloc[1], input_text.iloc[2], 
             chosen_philosopher, max_tokens, chosen_philosopher, chosen_philosopher)
    user_prompt_eng=translator.translate_text(user_prompt, target_lang="KO").text
    st.session_state.messages.append({"role": "user", 
                                      "content": user_prompt_eng+'@@@'+user_message})

    # OpenAI GPT-3.5-turbo를 사용해 응답 생성
    response = openai.chat.completions.create(
            model=selected_model_final,
            messages=st.session_state.messages, 
        )
    answer = translator.translate_text(response.choices[0].message.content, target_lang='KO').text
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": answer+'@@@'+chosen_philosopher})

# 대화 로그 및 상태 초기화 버튼들
if st.button("대화 다시 시작하기"):
    st.session_state.messages = []
    #st.session_state.messages = [
        #{"role": "system", 
         #"content": "You are %s. Do not act like a chatbot and just be %s himself" % (selected_prompt.split(' ')[9].replace(',','') , selected_prompt.split(' ')[9].replace(',',''))}
    #]

st.subheader("📝 대화 로그")
st.write("_________________________________________________________________________________________________________")
for message in st.session_state.messages:
    if message["role"] == "user":
        input_message = message['content'].split('@@@')[1]
        st.write("🙋‍♂나:")
        st.write(input_message)
        st.write("_________________________________________________________________________________________________________")
        # 정규식 패턴: 괄호 사이의 값을 찾음
        pattern = r'\((.*?)\)'    
        # 정규식을 사용하여 괄호 안의 값을 찾음
        matches = re.findall(pattern, input_message)
        st.write("참고 저서: " )
    elif message["role"] == "assistant":
        gpt_answer = message['content'].split('@@@')[0]
        st.write("🧔 %s: "%(message['content'].split('@@@')[1]))
        st.write(f"{gpt_answer}")
        st.write("_________________________________________________________________________________________________________")
            
