import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import threading
import time


mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose



def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle


def calculate_torso_lean(shoulder, hip):
    vertical_pt = [hip[0], hip[1] - 1.0]
    return calculate_angle(shoulder, hip, vertical_pt)



def speak(text):
    def run_tts():
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass

        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.say(text)
        engine.runAndWait()

    threading.Thread(target=run_tts, daemon=True).start()



counter = 0
stage = None
current_rep_valid = True
last_feedback_time = 0
FEEDBACK_COOLDOWN = 3.5


down_feedback_given = False  
in_motion_feedback_given = False  


cap = cv2.VideoCapture(0)

with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        try:
            landmarks = results.pose_landmarks.landmark
            h, w, _ = image.shape


            shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                     landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
            toe = [landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y]

     
            knee_angle = calculate_angle(hip, knee, ankle)
            torso_lean_angle = calculate_torso_lean(shoulder, hip)
            knee_ankle_x_diff = abs(knee[0] - ankle[0]) * w
            distance_knee_toe = (knee[0] - toe[0]) * w

          
            current_error_msg = None

            if torso_lean_angle > 45.0:
                current_error_msg = "Wyprostuj plecy!"
            elif knee_ankle_x_diff > 45:
                current_error_msg = "Utrzymaj stabilne kolano!"
            elif knee_angle < 100 and abs(distance_knee_toe) > 30 and (knee[0] < toe[0] or knee[0] > toe[0]):
                current_error_msg = "Wydłuż krok!"

  
            if current_error_msg:
                current_rep_valid = False
                current_time = time.time()
                if current_time - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak(current_error_msg)
                    last_feedback_time = current_time

           
            if knee_angle > 160:
                if stage == 'dol':
                    if current_rep_valid:
                        counter += 1
                        speak(f"Pięknie, {counter}")
                    else:
                        speak("Powtórzenie spalone. Skup się i zacznij jeszcze raz.")


                stage = 'gora'
                current_rep_valid = True
                down_feedback_given = False
                in_motion_feedback_given = False

        
            elif 100 <= knee_angle <= 140:
      
                if current_rep_valid and not in_motion_feedback_given and stage == 'gora':
                   
                    speak("Pomału w dół...")
                    in_motion_feedback_given = True

          
            elif knee_angle < 100:
                stage = 'dol'

                if current_rep_valid and not down_feedback_given:
                    speak("Dobre zejście, trzymaj napięcie i w górę!")
                    down_feedback_given = True

       
            cv2.rectangle(image, (0, 0), (250, 73), (245, 117, 16), -1)
            cv2.putText(image, 'POWTORZENIA', (15, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(image, str(counter), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.putText(image, 'STATUS', (130, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(image, stage if stage else "Czekam", (130, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2,
                        cv2.LINE_AA)

            if current_error_msg:
                cv2.putText(image, current_error_msg, (15, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        except Exception as e:
            pass

        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        cv2.imshow('Cyber Trener - Bulgarski Przysiad', image)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
