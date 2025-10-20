import asyncio
from quart import Quart, request
from app.services.settings_service import SettingsService 

class ApiServer:
    """
    Асинхронний веб-сервер на базі Quart, що працює в одному
    циклі подій з основним додатком.
    """
    def __init__(self,settings: SettingsService):

        self.settings_service = settings
        self.quart_app = Quart(__name__)
        
        # Створюємо "заглушки" для callback-функцій, які будуть передані з MainWindow
        self.on_rf_data = lambda data: print("Попередження: обробник для RF даних не встановлено.")
        self.on_audio_alert = lambda status: print("Попередження: обробник для аудіо-тривоги не встановлено.")

        self.server_task: asyncio.Task | None = None

        # Реєструємо асинхронні маршрути (endpoints)
        self.quart_app.route('/api/2_4_ghz', methods=['POST'])(self.receive_rf_data)
        self.quart_app.route('/api/audio_alarm', methods=['POST'])(self.receive_audio_alarm)

    async def run_server(self):
        """Асинхронно запускає сервер."""
        host=self.settings_service.host
        port =self.settings_service.port
        print(f"Асинхронний сервер Quart запущено на http://{host}:{port}")
        try:
            # Запускаємо сервер
            self.server_task = asyncio.create_task(
    self.quart_app.run_task(host=host, port=port)
    )
        except asyncio.CancelledError:
            # Це нормально при закритті програми
            print("Сервер зупинено.")

    # Обробники тепер є асинхронними функціями
    async def receive_rf_data(self):
        analyzed_results = await request.get_json()
        if analyzed_results:
            # Просто передаємо його далі, без аналізу
            self.on_rf_data(analyzed_results)
        return 'RF data received'

    async def receive_audio_alarm(self):
        """Асинхронний обробник для маршруту /api/audio_alarm."""
        status_data = await request.get_json()
        if status_data and 'alert' in status_data:
            alert_status = status_data['alert'].lower() == 'true'
            # Викликаємо callback-функцію, передану з MainWindow
            self.on_audio_alert(alert_status)
        return 'Audio alert received'
    
    def stop_server(self):
        """Асинхронно зупиняє сервер."""
        #await self.quart_app.shutdown()
        if(self.server_task):
            self.server_task.cancel()
        # if self.server_task and not self.server_task.done():
        #     self.server_task.cancel()
        #     try:
        #         await self.server_task
        #     except asyncio.CancelledError:
        #         pass
        #     await self.quart_app.shutdown()
        #     print("Сервер Quart успішно зупинено.")
        #print(asyncio.tasks.all_tasks())