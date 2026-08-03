import threading


class CameraAssistant:

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.preview_thread = None
        self.preview_running = False
        self.capture = None

    def camera_available(self):
        try:
            import cv2
            return True
        except Exception:
            return False

    def inspect_scene(self):
        if not self.camera_available():
            return {
                "ok": False,
                "message": "Kamera desteği bulunamadı. opencv-python paketini yükleyin."
            }

        import cv2
        try:
            self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
            if not self.capture.isOpened():
                return {
                    "ok": False,
                    "message": "Kamera açılamadı. Başka bir kamera indeksini deneyin, veya cihaz izinlerini kontrol edin."
                }

            ret, frame = self.capture.read()
            if not ret or frame is None:
                return {
                    "ok": False,
                    "message": "Kamera çerçevesi alınamadı. Işık, kadraj ya da donanımı kontrol edin."
                }

            faces = self._count_faces(frame)
            brightness = self._frame_brightness(frame)
            description = self._describe_frame(frame, faces, brightness)
            return {
                "ok": True,
                "message": description,
                "faces": faces,
                "brightness": brightness,
            }
        except Exception as e:
            return {
                "ok": False,
                "message": f"Kamera görüntüsü işlenemedi: {e}"
            }
        finally:
            self._cleanup_capture()

    def _describe_frame(self, frame, faces, brightness):
        if faces > 0:
            return (
                f"Kamerada {faces} yüz tespit ettim. Sahne canlı ve algıya hazır. "
                "Işık seviyesi yeterliyse, yüz hareketi ve mimikleri rahatça izleyebilirim."
            )

        if brightness < 40:
            return (
                "Kamerada yüz algılayamadım. Görüntü karanlık, lütfen ortam ışığını artır veya kamerayı yüzüne çevir."
            )

        return (
            "Kamerada yüz tespit edemedim. "
            "Kameranın kadrajını biraz daha yukarı çek veya hareketini hızlandır; "
            "böylece sahneye daha hızlı girerim."
        )

    def _frame_brightness(self, frame):
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return int(gray.mean())
        except Exception:
            return 0

    def _count_faces(self, frame):
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            return len(faces)
        except Exception:
            return 0

    def start_preview(self):
        if not self.camera_available():
            return {
                "ok": False,
                "message": "Kamera başlatılamadı. opencv-python yüklü değil."
            }

        if self.preview_running:
            return {
                "ok": False,
                "message": "Kamera önizleme zaten çalışıyor."
            }

        self.preview_running = True
        self.preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self.preview_thread.start()

        return {
            "ok": True,
            "message": "Kamera önizleme başlatıldı. Canlı görüntü penceresi açıldı; çıkmak için pencereye odaklanıp 'q' tuşuna basabilirsin."
        }

    def stop_preview(self):
        self.preview_running = False
        if self.preview_thread:
            self.preview_thread.join(timeout=1)

        self._cleanup_capture()

        return {
            "ok": True,
            "message": "Kamera önizleme durduruldu."
        }

    def _preview_loop(self):
        import cv2
        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)

        if not self.capture.isOpened():
            self.preview_running = False
            return

        cv2.namedWindow('Astra Kamera Önbakışı', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Astra Kamera Önbakışı', 640, 480)

        while self.preview_running:
            ret, frame = self.capture.read()
            if not ret:
                break

            cv2.imshow('Jarvis Kamera Önbakışı', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.preview_running = False
        self._cleanup_capture()
        cv2.destroyAllWindows()

    def _cleanup_capture(self):
        try:
            if self.capture is not None:
                self.capture.release()
                self.capture = None
        except Exception:
            pass
