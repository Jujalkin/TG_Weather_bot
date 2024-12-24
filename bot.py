from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import asyncio
from aiogram.types import InputFile
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from config import BOT_TOKEN
from app import get_location_key, get_weather
from aiogram.types import BufferedInputFile


# Логирование
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния
class WeatherStates(StatesGroup):
    waiting_for_start_point = State()
    waiting_for_end_point = State()
    waiting_for_stops = State()
    waiting_for_interval = State()
    waiting_for_graph_feature = State()


# Функция для создания клавиатуры выбора интервала
def get_interval_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 день", callback_data="interval_1"),
            InlineKeyboardButton(text="3 дня", callback_data="interval_3")
        ],
        [
            InlineKeyboardButton(text="5 дней", callback_data="interval_5")
        ]
    ])
    return keyboard


# Функция для создания клавиатуры выбора характеристики для графика
def get_graph_feature_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Температура", callback_data="feature_temp"),
            InlineKeyboardButton(text="Влажность", callback_data="feature_humidity")
        ],
        [
            InlineKeyboardButton(text="Скорость ветра", callback_data="feature_wind"),
            InlineKeyboardButton(text="Вероятность осадков", callback_data="feature_precipitation")
        ]
    ])
    return keyboard

# Старт
@dp.message(F.text == '/start')
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот-предсказатель погоды!\n"
        "Укажи точки маршрута, а я предоставлю тебе данные о погоде!\n"
        "Используй /weather для начала работы или /help для справки"
    )

# Помощь
@dp.message(F.text == '/help')
async def cmd_help(message: types.Message):
    await message.answer(
        "*Привет! Я бот-предсказатель погоды!*\n\n"
        "Я помогу тебе узнать погоду на маршруте, который ты укажешь. Вот как это работает:\n"
        "1. Напиши команду `/weather`, чтобы начать.\n"
        "2. Укажи город - начало маршрута.\n"
        "3. Укажи город - конец маршрута.\n"
        "4. Если нужно, добавь промежуточные точки маршрута.\n"
        "5. Выбери интервал прогноза (1, 3 или 5 дней).\n"
        "6. Выбери характеристику для построения графика (температура, влажность, ветер, осадки).\n"
        "7. Получи прогноз погоды и график!\n\n"
        "*Доступные команды:*\n"
        "- `/start` — Начать общение с ботом.\n"
        "- `/weather` — Начать процесс получения погоды.\n"
        "- `/help` — Показать эту справку.\n\n"
        "*Пример использования:*\n"
        "1. `/weather`\n"
        "2. Введите город: Москва\n"
        "3. Введите город: Санкт-Петербург\n"
        "4. Добавьте промежуточные точки (если нужно): Нижний Новгород, Казань\n"
        "5. Выберите интервал: 3 дня\n"
        "6. Выберите характеристику: Температура\n"
        "7. Получите прогноз и график!\n\n"
        "Если у вас возникнут вопросы, напишите мне: @bardachell. Приятного использования! :>"
    )

# Начальная точка
@dp.message(F.text == '/weather')
async def cmd_weather(message: types.Message, state: FSMContext):
    await state.set_state(WeatherStates.waiting_for_start_point)
    await message.answer("Введите город - начало маршрута: ")

# Конечная точка
@dp.message(WeatherStates.waiting_for_start_point)
async def process_start_point(message: types.Message, state: FSMContext):
    await state.update_data(start_point=message.text)
    await state.set_state(WeatherStates.waiting_for_end_point)
    await message.answer("Введите город - конец маршрута:")

# Добавлять промежуточные точки?
@dp.message(WeatherStates.waiting_for_end_point)
async def process_end_point(message: types.Message, state: FSMContext):
    await state.update_data(end_point=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="add_stops"),
            InlineKeyboardButton(text="Нет", callback_data="no_stops")
        ]
    ])
    await message.answer("Хотите добавить промежуточные точки маршрута?", reply_markup=keyboard)

# Ввод промежуточных точек
@dp.callback_query(F.data == "add_stops")
async def process_add_stops(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(WeatherStates.waiting_for_stops)
    await callback.message.answer("Введите промежуточные точки маршрута через запятую:")
    await callback.answer()

# Без остановок
@dp.callback_query(F.data == "no_stops")
async def process_no_stops(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(stops=[])
    await callback.message.answer("Выберите интервал для прогноза погоды: ", reply_markup=get_interval_keyboard())
    await callback.answer()

# С остановками
@dp.message(WeatherStates.waiting_for_stops)
async def process_stops(message: types.Message, state: FSMContext):
    stops = [stop.strip() for stop in message.text.split(',')]
    await state.update_data(stops=stops)
    await message.answer("Выберите интервал для прогноза погоды: ", reply_markup=get_interval_keyboard())

# Вывод данных по городам и дням
@dp.callback_query(F.data.startswith("interval_"))
async def process_interval(callback: types.CallbackQuery, state: FSMContext):
    interval = int(callback.data.split("_")[1])
    data = await state.get_data()

    route_points = [data['start_point']]
    if 'stops' in data:
        route_points.extend(data['stops'])
    route_points.append(data['end_point'])

    await callback.message.answer(
        f"Собираю информацию о погоде для вашего маршрута на {interval} {'день' if interval == 1 else 'дня' if interval < 5 else 'дней'}...")

    forecasts_data = []
    for point in route_points:
        location_key = get_location_key(point)
        if not location_key:
            await callback.message.answer(f"Не удалось найти локацию: {point}")
            continue

        forecasts, dates, temps = get_weather(location_key, interval)
        if forecasts and dates and temps:
            forecasts_data.append((point, forecasts, dates, temps))

            # Отправляем текстовый прогноз
            forecast_text = f"Прогноз погоды для {point} на {interval} {'день' if interval == 1 else 'дня' if interval < 5 else 'дней'}:\n\n"
            for forecast in forecasts:
                forecast_text += (
                    f"{forecast['date']}:\n"
                    f"Температура: {forecast['temp']}°C\n"
                    f"Влажность: {forecast['humidity']}%\n"
                    f"Ветер: {forecast['wind']} км/ч\n"
                    f"{forecast['description'].capitalize()}\n\n"
                )
            await callback.message.answer(forecast_text)

    await state.update_data(forecasts_data=forecasts_data)
    await callback.message.answer("Выберите характеристику для построения графика: ", reply_markup=get_graph_feature_keyboard())
    await callback.answer()

# Построение графика
@dp.callback_query(F.data.startswith("feature_"))
async def process_graph_feature(callback: types.CallbackQuery, state: FSMContext):
    feature = callback.data.split("_")[1]
    data = await state.get_data()
    forecasts_data = data.get('forecasts_data', [])

    if not forecasts_data:
        await callback.message.answer("Нет данных для построения графика :<")
        await callback.answer()
        return

    # Создаем график
    plt.figure(figsize=(10, 6))
    for point, forecasts, dates, temps in forecasts_data:
        if feature == "temp":
            values = [forecast['temp'] for forecast in forecasts]
            label = "Температура (°C)"
        elif feature == "humidity":
            values = [forecast['humidity'] for forecast in forecasts]
            label = "Влажность (%)"
        elif feature == "wind":
            values = [forecast['wind'] for forecast in forecasts]
            label = "Скорость ветра (км/ч)"
        elif feature == "precipitation":
            values = [forecast['precipitation'] for forecast in forecasts]
            label = "Вероятность осадков (%)"

        plt.plot(dates, values, label=f"{point}")

    plt.xlabel("Дата")
    plt.ylabel(label)
    plt.title(f"График погоды по маршруту ({feature.capitalize()})")
    plt.legend()
    plt.grid(True)

    # Сохраняем график в буфер
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Преобразуем BytesIO в BufferedInputFile
    photo = BufferedInputFile(buf.read(), filename="weather_graph.png")

    # Отправляем график пользователю
    await callback.message.answer_photo(photo=photo, caption=f"График погоды по маршруту ({feature.capitalize()})")
    await callback.answer()


# Обработчик иных сообщений
@dp.message()
async def handle_unknown_message(message: types.Message):
    await message.answer('Извините, я не понял ваш запрос. Пожалуйста, напишите /start и следуйте инструкциям')

if __name__ == '__main__':
    try:
        asyncio.run(dp.start_polling(bot))
    except Exception as e:
        logging.error(f'Ошибка при запуске бота: {e}')