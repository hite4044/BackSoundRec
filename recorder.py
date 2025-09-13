import os
import random
import wave
from datetime import datetime
from io import BytesIO
from os import makedirs
from os.path import expandvars, join, isfile
from queue import Queue, Empty
from threading import Thread, Event
from time import sleep, time
from typing import Optional, List

import pyaudio

from lib import log as logger
from record_lib.auto_startup import set_auto_startup_no_error
from record_lib.config import config
from lib.data import RecordArgs, format_time
from record_lib.record_manager import rec_file_manager
from record_lib.shutdown_listener import ShutdownListener


def generate_args():
    return RecordArgs(
        format=config.audio_format,
        output_format=config.audio_output_format,
        channels=config.audio_channels,
        rate=config.audio_rate,
        chunk=config.audio_chunk,
        record_seconds=config.audio_seg_duration
    )


class RecordSessionManager:
    def __init__(self):
        self.py_audio = pyaudio.PyAudio()
        self.args_update_event = Event()
        self.rec_thread = Thread(target=self.run, daemon=True)
        self.rec_thread.start()
        self.shutdown_listener = ShutdownListener(config.shutdown_listener_title)
        Thread(target=self.shutdown_listener.start, daemon=True).start()

    def run(self):
        launch_try_times = 0
        logger.info(f"程序配置 -> "
                    f"录音输出格式: {config.audio_output_format}, "
                    f"采样格式: {config.audio_format}, "
                    f"声道数: {config.audio_channels}, "
                    f"采样率: {config.audio_rate}, "
                    f"数据块大小: {config.audio_chunk}, "
                    f"分段时长: {config.audio_seg_duration}s, "
                    f"保存比特率: {config.audio_bitrate}, "
                    f"保存路径: {config.audio_save_path}")
        while True:
            now = datetime.now()
            month_dir = join(expandvars(config.audio_save_path), "audio", now.strftime("%Y-%m"))
            makedirs(month_dir, exist_ok=True)
            day_dir = join(month_dir, now.strftime("%Y-%m-%d"))
            makedirs(day_dir, exist_ok=True)

            args = generate_args()
            session = RecordSession(self.py_audio, args, day_dir)
            ret = session.start_record()
            if config.rec_start_failed_stop != 0 and launch_try_times >= config.rec_start_failed_stop:
                config.save()
                logger.error(f"尝试次数过多, 录音启动失败")
                break
            if not ret:
                launch_try_times += 1
                logger.error(f"录音启动失败, 已尝试{launch_try_times}次")
                sleep(config.rec_start_failed_wait)
                continue
            launch_try_times = 0

            def save_func():
                session.stop_record()
                save_over_flag.wait()

            save_over_flag = Event()
            self.shutdown_listener.set_save_func(save_func)
            while True:
                session.thread.join(timeout=1)
                if not session.thread.is_alive():
                    break
                if self.args_update_event.is_set():
                    session.stop_record()
                    self.args_update_event.clear()
                    break


            rec_start = datetime.fromtimestamp(session.rec_time_range[0])
            rec_end = datetime.fromtimestamp(session.rec_time_range[1])
            file_name = f'{rec_start.strftime("%Y-%m-%d %H-%M-%S")} ~ {rec_end.strftime("%H-%M-%S")}.{config.audio_file_format}'
            file_path = join(day_dir, file_name)
            session.save_record(file_path, self.shutdown_listener.is_shutdown)
            if self.shutdown_listener.is_shutdown:
                config.save()
                rec_file_manager.stop()
                save_over_flag.set()
                break


class RecordSession:
    def __init__(self, py_audio: pyaudio.PyAudio, args: RecordArgs, record_dir: str):
        self.stream: Optional[pyaudio.Stream] = None
        self.py_audio = py_audio
        self.audio_format = args.output_format
        self.args = args
        self.thread_events = Queue()
        self.audio_data_io = BytesIO()
        self.thread: Optional[Thread] = None
        self.rec_time_range: List[float] = [time(), time()]
        self.id = hex(int.from_bytes(random.randbytes(4), "big"))[2:].zfill(8)

        self.record_fp = join(record_dir, f'{datetime.now().strftime("%Y-%m-%d %H-%M-%S")} - TEMP.wav')

    def start_record(self):
        args = self.args
        if self.thread and self.thread.is_alive():
            logger.info(f"[{self.id}] 开始录音前尝试停止录音")
            self.stop_record()
            self.thread = None
        try:
            self.stream = self.py_audio.open(format=args.format,
                                             channels=args.channels,
                                             rate=args.rate,
                                             input=True,
                                             frames_per_buffer=args.chunk)
            logger.info(f"[{self.id}] "
                        f"开始录音 -> "
                        f"录音输出格式: {args.output_format}, "
                        f"采样格式: {args.format}, "
                        f"位深度: {self.py_audio.get_sample_size(args.format)}, "
                        f"声道数: {args.channels}, "
                        f"采样率: {args.rate}, "
                        f"数据块大小: {args.chunk}, "
                        f"时长: {args.record_seconds}s")
        except Exception as e:
            logger.error(f"[{self.id}] 录音启动失败 -> {e.__class__.__name__}: {e}")
            return False
        self.thread = Thread(target=self.record_thread, args=(self.stream,), daemon=True)
        self.thread.start()
        return True

    def stop_record(self):
        logger.info(f"[{self.id}] 尝试停止录音")
        if not self.thread:
            return None
        if self.thread.is_alive():
            self.thread_events.put("stop")
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                logger.info(f"[{self.id}] 录音无法结束")
                return False
            logger.info(f"[{self.id}] 录音已停止")
        else:
            logger.warning(f"[{self.id}] 录音自行停止")
        return True

    def record_thread(self, stream: pyaudio.Stream):
        args = self.args
        audio_data_io = self.audio_data_io
        with wave.open(self.record_fp, 'wb') as wav_file:
            wav_file.setnchannels(args.channels)
            wav_file.setsampwidth(self.py_audio.get_sample_size(self.args.format))
            wav_file.setframerate(args.rate)

            error_counter = 0
            self.rec_time_range[0] = time()
            for _ in range(0, int(args.rate / args.chunk * args.record_seconds) + 1):
                try:
                    data = stream.read(args.chunk)
                    wav_file.writeframes(data)
                    audio_data_io.write(data)
                    self.rec_time_range[1] = time()
                except Exception as e:
                    logger.error(f"[{self.id}] 录音过程中异常 -> {e.__class__.__name__}: {e}")
                    error_counter += 1
                    if error_counter >= config.recording_failed_stop:
                        logger.error(f"[{self.id}] 录音异常次数过多 -> 录音已停止")
                        break
                    sleep(config.recording_failed_wait)
                try:
                    event = self.thread_events.get_nowait()
                    if event == "stop":
                        logger.info(f"[{self.id}] 退出录音线程")
                        break
                except Empty:
                    pass

    def save_record(self, file_path: str, shutdown_save: bool = False) -> bool:
        try:
            if isfile(file_path):
                os.remove(file_path)
            temp_wav_path = "".join(file_path.split(".")[:-1]) + " - TEMP.wav"
            os.rename(self.record_fp, temp_wav_path)
            if shutdown_save:
                return True

            args = self.args
            logger.info(f"[{self.id}] 添加录音保存任务 -> 输出格式: {args.output_format}, "
                        f"录音时长: {format_time(self.rec_time_range[1] - self.rec_time_range[0])}")
            self.audio_data_io.seek(0)
            rec_file_manager.add_task(temp_wav_path, args, file_path)
            return True
        except Exception as e:
            logger.error(f"[{self.id}] 录音保存任务创建失败 -> {e.__class__.__name__}: {e}")
            return False


set_auto_startup_no_error()
manager = RecordSessionManager()
while manager.rec_thread.is_alive():
    try:
        manager.rec_thread.join(timeout=1)
    except KeyboardInterrupt:
        break
