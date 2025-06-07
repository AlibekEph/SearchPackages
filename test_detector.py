import requests
import argparse
from pathlib import Path
import os
import json
from typing import Dict, Any
import webbrowser
import time

def test_detector(image_path: str, object_name: str) -> Dict[str, Any]:
    """
    Тестирует API детектора объектов
    
    Args:
        image_path: путь к тестовому изображению
        object_name: название объекта для поиска
    Returns:
        Dict с результатами детекции
    """
    url = "http://localhost:8008/detect_object"
    
    # Проверяем существование файла
    if not Path(image_path).exists():
        print(f"Ошибка: файл {image_path} не найден")
        return {}
    
    # Подготавливаем файл для отправки
    files = {
        'file': ('image.jpg', open(image_path, 'rb'), 'image/jpeg')
    }
    
    # Параметры запроса
    params = {
        'object_name': object_name
    }
    
    try:
        # Отправляем запрос
        response = requests.post(url, files=files, params=params)
        
        # Проверяем статус ответа
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка: {response.status_code}")
            print(response.text)
            return {}
            
    except requests.exceptions.ConnectionError:
        print("Ошибка: Не удалось подключиться к серверу. Убедитесь, что сервер запущен на http://localhost:8008")
        return {}
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        return {}
    finally:
        # Закрываем файл
        files['file'][1].close()

def process_test_folder(folder_path: str, object_name: str):
    """
    Обрабатывает все изображения в указанной папке
    
    Args:
        folder_path: путь к папке с тестовыми изображениями
        object_name: название объекта для поиска
    """
    # Проверяем существование папки
    if not Path(folder_path).exists():
        print(f"Ошибка: папка {folder_path} не найдена")
        return
    
    # Получаем список всех изображений
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    image_files = [f for f in Path(folder_path).iterdir() if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"Ошибка: в папке {folder_path} не найдено изображений")
        return
    
    print(f"Найдено {len(image_files)} изображений")
    
    # Словарь для хранения результатов
    all_results = {}
    # Список для сортировки по вероятности
    results_list = []
    
    # Обрабатываем каждое изображение
    for image_file in image_files:
        print(f"\nОбработка {image_file.name}...")
        result = test_detector(str(image_file), object_name)
        
        if result:
            all_results[image_file.name] = result
            
            # Добавляем результат в список для сортировки
            clip_results = result['results']['clip']
            if clip_results:
                pred = clip_results[0]
                results_list.append({
                    'filename': image_file.name,
                    'probability': pred['probability'],
                    'prompt': pred['best_prompt'],
                    'path': str(image_file)
                })
    
    # Сортируем результаты по вероятности (по убыванию)
    results_list.sort(key=lambda x: x['probability'], reverse=True)
    
    # Выводим топ-3 результата
    print("\nТоп-3 изображения с наибольшей вероятностью:")
    print("-" * 80)
    for i, result in enumerate(results_list[:3], 1):
        print(f"{i}. {result['filename']}")
        print(f"   Вероятность: {result['probability']:.3f}")
        print(f"   Промпт: '{result['prompt']}'")
        print("-" * 80)
    
    # Сохраняем все результаты в JSON файл
    output_file = f"detection_results_{object_name}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nВсе результаты сохранены в {output_file}")
    
    # Открываем третье изображение
    if len(results_list) >= 3:
        third_image = results_list[2]
        print(f"\nОткрываю третье изображение: {third_image['filename']}")
        webbrowser.open(f"file://{third_image['path']}")
        time.sleep(1)  # Даем время на открытие изображения

def main():
    parser = argparse.ArgumentParser(description='Тестирование API детектора объектов')
    parser.add_argument('folder_path', help='Путь к папке с тестовыми изображениями')
    parser.add_argument('object_name', help='Название объекта для поиска')
    
    args = parser.parse_args()
    process_test_folder(args.folder_path, args.object_name)

if __name__ == "__main__":
    main() 