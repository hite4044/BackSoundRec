import subprocess
import wave
from os import remove, listdir, stat
from os.path import join, expandvars, isfile, isdir
from queue import Queue, Empty
from threading import Thread, Event
from typing import Optional
from wave import Wave_read

from pydub import AudioSegment
from pydub import audio_segment
from win32.Demos.RegRestoreKey import temp_dir

from lib import log as logger
from record_lib.config import config
from lib.data import RecordArgs, format_file_size
from lib.perf import Counter

ACTIVE_PROC: Optional[subprocess.Popen] = None


class HackedPopen(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        kwargs["shell"] = True
        kwargs["stdin"] = subprocess.PIPE
        super().__init__(*args, **kwargs)

    def communicate(self, input_=None, timeout=None):
        global ACTIVE_PROC
        ACTIVE_PROC = self
        return super().communicate(input_, timeout)



class RecordFileManager:
    def __init__(self):
        self.queue = Queue()
        self.stop_flag = Event()
        self.thread = Thread(target=self.data_save_thread, daemon=True)
        self.thread.start()
        Thread(target=self.add_non_complete_task, daemon=True).start()

    def add_non_complete_task(self):
        audio_dir = join(expandvars(config.audio_save_path), "audio")
        if not isdir(audio_dir):
            return
        for month_name in listdir(audio_dir):
            month_dir = join(audio_dir, month_name)
            for day_name in listdir(month_dir):
                day_dir = join(month_dir, day_name)
                for file_name in listdir(day_dir):
                    if file_name.endswith(" - TEMP.wav"):
                        logger.info(f"添加关机前保存的临时wav任务 {file_name}")
                        wav_path = join(day_dir, file_name)
                        wav_file: Wave_read = wave.open(wav_path, "rb")
                        args = RecordArgs(
                            config.audio_format,
                            config.audio_output_format,
                            wav_file.getnchannels(),
                            wav_file.getframerate(),
                            config.audio_chunk,
                            wav_file.getnframes() / wav_file.getframerate()
                        )
                        file_path = join(day_dir, file_name.replace(" - TEMP.wav", f".{config.audio_file_format}"))
                        if isfile(file_path):
                            remove(file_path)
                        self.add_task(wav_path, args, file_path)
                        wav_file.close()

    def data_save_thread(self):
        while not self.stop_flag.is_set():
            try:
                data = self.queue.get(timeout=1)
                self.save_record(*data)
            except Empty:
                continue

    def stop(self):
        self.stop_flag.set()
        ACTIVE_PROC.terminate()
        self.thread.join(timeout=config.record_save_join_timeout)

    def add_task(self, wav_path: str, args: RecordArgs, file_path: str):
        self.queue.put((wav_path, args, file_path))

    @staticmethod
    def save_record(temp_wav_file: str, args: RecordArgs, file_path: str):
        try:
            timer = Counter(create_start=True)

            audio = AudioSegment.from_wav(temp_wav_file)

            audio.export(file_path, format=args.output_format, bitrate=config.audio_bitrate)
            if isfile(file_path):
                remove(temp_wav_file)
                file_size = format_file_size(stat(file_path).st_size)
                logger.debug(
                    f"录音保存成功 -> 耗时: {timer.endT()}, 文件大小: {file_size}, 文件地址: {file_path}")
        except Exception as e:
            logger.error(f"录音保存失败 -> {e.__class__.__name__}: {e}")


audio_segment.subprocess.Popen = HackedPopen
rec_file_manager = RecordFileManager()
