import gradio as gr
import os
import google.generativeai as genai
import json

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-2.0-flash-exp",
  generation_config=generation_config,
)

class Quiz:
    def __init__(self):
        self.questions=[]
        self.options=[]
        self.answers=[]
        self.option_buttons=[gr.Button(f'Option Button {x+1}', visible=False) for x in range(4)]
        self.current_question_index = -1
        self.questionsLoaded = False
        self.score = 0
        self.failed = False
        self.map={0:'A', 1:'B', 2:'C', 3:'D'}
    
    def generate_quiz(self, user_input):
        chat_session = model.start_chat(
        history=[]
        )

        response = chat_session.send_message(f"""I need you to act as a quiz generator. You will be provided with the quiz topic and your task is to create a 5-question multiple-choice quiz based on that information. 
                Each question must have 4 distinct answer choices (A, B, C, and D), and you need to clearly indicate the correct answer for each. 

                Quiz topic: {user_input}

                Return the JSON directly and nothing else. Don't write json in the output. The final output must be formatted in JSON, following this structure:
                
                {{
                "questions": [
                    {{
                    "question": "Question 1 Text",
                    "options": [
                        "Option A",
                        "Option B",
                        "Option C",
                        "Option D"
                    ],
                    "answer": "Correct Answer Letter (A, B, C, or D)"
                    }}
                ]
                }}""")

        self.questions=[]
        self.options=[]
        self.answers=[]
        data=response.text
        cleaned_data=data[7:]
        cleaned_data=cleaned_data[:-4]
        quiz_data=json.loads(cleaned_data)
        self.questionsLoaded = True
        for content in quiz_data["questions"]:
            self.questions.append(content["question"])
            self.options.append(content["options"])
            self.answers.append(content["answer"])
        gr.Info("Questions loaded", duration=5)
        return gr.update(value="")
    
    def update_quiz(self):
        updates=[]
        if self.questionsLoaded:
            self.failed = False
            self.current_question_index+=1
            question = [self.questions[self.current_question_index] if self.current_question_index < len(self.questions) else None ] 
            if question[0] is not None:
                question=''.join(question)
                updates.append(gr.update(value=f"# {question}", visible=True))
                for option in self.options[self.current_question_index]:
                    updates.append(gr.update(value=option, visible=True, interactive=True))
                
                if(self.current_question_index==len(self.questions)):
                    updates.append(gr.append(visible=True, min_width=20))
                    updates.append(gr.update(visible=False))
                else:
                    updates.append(gr.update(visible=False))
                    updates.append(gr.update(value="Next"))
            else:
                markdown=f"""# <center> Quiz over! </center>
                                ## <center> You scored {self.score}/{len(self.questions)} </center>
                            """
                updates=[markdown]
                for option in self.options[self.current_question_index-1]:
                    updates.append(gr.update(visible=False))
                updates.append(gr.update(visible=True))
                updates.append(gr.update(visible=False))
        else:
            gr.Info('Please add quiz topic', duration=5)

        return updates

    def check_answer(self, button):
        correct_answer = self.answers[self.current_question_index]
        updates=[]
        button_index = self.options[self.current_question_index].index(button)
        option_letter = self.map[button_index]
        if option_letter == correct_answer:
            gr.Info('Correct answer!', duration=2)
            if self.failed == False:
                self.score+=1
            for option in self.options[self.current_question_index]:
                if option == option_letter:
                    updates.append(gr.update(interactive=False, variant='primary'))
                else:
                    updates.append(gr.update(interactive=False, variant='secondary'))
        else:
            gr.Info('Try again!', duration=2)
            self.failed=True
            for option in self.options[self.current_question_index]:
                if option==button:
                    updates.append(gr.update(interactive=False, variant='secondary'))
                else:
                    updates.append(gr.update())
        return updates
    
    def restart_quiz(self):
        self.current_question_index = -1
        self.questionsLoaded = False
        self.score = 0
        self.failed = False
        updates=[]
        updates.append(gr.update(visible=False))
        updates.append(gr.update(visible=True))
        updates.append(gr.update(value='Start', visible=True))
        updates.append(gr.update(visible=False))
        return updates
        

user_quiz=Quiz()

with gr.Blocks() as demo:

    heading = gr.Markdown("# Quizbot")
    user_input = gr.Textbox(placeholder="Enter Topic", interactive=True)
    user_input.submit(user_quiz.generate_quiz, [user_input], user_input).then(
        lambda: gr.update(visible=False) if user_quiz.questionsLoaded else gr.update(),
        outputs=user_input
    )

    question = gr.Markdown("# Question", visible=False)
    with gr.Row():
        user_quiz.option_buttons[0].render()
        user_quiz.option_buttons[1].render()
    with gr.Row():
        user_quiz.option_buttons[2].render()
        user_quiz.option_buttons[3].render()
    
    for button in user_quiz.option_buttons:
        button.click(user_quiz.check_answer, button, [*user_quiz.option_buttons])

    next_button=gr.Button(value='Start', variant='stop')
    restart_button=gr.Button(value='Restart quiz', visible=False)
    next_button.click(user_quiz.update_quiz, [], [question, *user_quiz.option_buttons, restart_button, next_button])
    restart_button.click(user_quiz.restart_quiz, [], [question, user_input, next_button, restart_button])

    demo.launch(server_name='0.0.0.0')