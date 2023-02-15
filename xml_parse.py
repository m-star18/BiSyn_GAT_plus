import xmltodict
import json

import parse_tree


EN_TRAIN_XML = 'data/xml/ABSA16_Restaurants_Train_SB1_v2.xml'
EN_TEST_XML = 'data/xml/EN_REST_SB1_TEST.xml'
SP_TRAIN_XML = 'data/xml/SemEval-2016ABSA Restaurants-Spanish_Train_Subtask1.xml'
SP_TEST_XML = 'data/xml/SP_REST_SB1_TEST.xml'
FR_TRAIN_XML = 'data/xml/ABSA16FR_Restaurants_Train-withcontent.xml'
FR_TEST_XML = 'data/xml/ABSA16FR_Restaurants_Gold-withcontent.xml'
RU_TRAIN_XML = 'data/xml/se16_ru_rest_train.xml'
RU_TEST_XML = 'data/xml/EN_REST_SB1_TEST.xml'
TU_TRAIN_XML = 'data/xml/reviews.xml'
TU_TEST_XML = 'data/xml/TU_REST_SB1_TEST.xml'


def opinion_parse(sentence):
    # from ~ toの値を求める(単語抽出)
    aspect_word = []
    flag = False
    for opinion in sentence["Opinions"]["Opinion"]:
        if type(opinion) is not dict:
            opinion = sentence["Opinions"]["Opinion"]
            flag = True
        opinion["@target"] = opinion["@target"].encode("utf8").decode('unicode-escape').encode('latin1').decode('utf8')
        opinion["@target"] = opinion["@target"].replace('(', '').replace(')', '').replace('/', '')
        opinion["@target"] = opinion["@target"].replace(';', '').replace('<+>', '').replace('<->', '')
        if opinion["@target"] == "NULL":
            continue
        aspect_word.append(opinion["@target"].split(' '))
        if flag:
            break
    if aspect_word == [''] or not aspect_word:
        return None

    return aspect_word


def word_parse(sentence, aspect_word):
    spell = ''
    split_sentence = []
    aspect_from_to_index = [[0] * 3 for _ in range(len(aspect_word))]

    for word in sentence["text"].encode("utf8").decode('unicode-escape').encode('latin1').decode('utf8'):
        if word in ['(', ')', '/', ';', '/', '<', '+', '>', '*', ':', '@', '[', ']', '-']:
            continue
        if word == ' ':
            if spell != '':
                split_sentence.append(spell)
                spell = ''
        elif word == '.' or word == ',' or word == '!':
            if spell != '':
                split_sentence.append(spell)
                split_sentence.append(word)
            spell = ''
        else:
            spell += word

    if spell != '':
        split_sentence.append(spell)
    # 単語の位置を求める from to
    for i, word in enumerate(split_sentence):
        for j, as_word in enumerate(aspect_word):
            if word == as_word[aspect_from_to_index[j][2]]:
                if aspect_from_to_index[j][2] == 0 and aspect_from_to_index[j][1] == 0:
                    aspect_from_to_index[j][0] = i
                aspect_from_to_index[j][2] += 1
                if aspect_from_to_index[j][2] == len(as_word):
                    aspect_from_to_index[j][1] = i + 1
                    aspect_from_to_index[j][2] = 0
            else:
                aspect_from_to_index[j][2] = 0
    return aspect_from_to_index, split_sentence


def sentence_parse(sentence):
    data = {}
    aspects = []
    aspect_details = []

    if 'Opinions' not in sentence:
        return None

    if not sentence["Opinions"]:
        return None

    aspect_word = opinion_parse(sentence)
    if not aspect_word:
        return None

    # 単語をいい感じに分割 token...
    aspect_from_to_index, split_sentence = word_parse(sentence, aspect_word)

    # debug
    # print(aspect_from_to_index, aspect_word, sentence["text"])

    # アスペクトの部分 aspects + aa_choice
    index = 0
    for opinion in sentence["Opinions"]["Opinion"]:
        if type(opinion) is not dict:
            return None
        # targetが定まってないやつはやらない
        if opinion["@target"] == "NULL":
            continue
        # assert
        if aspect_from_to_index[index][0] > aspect_from_to_index[index][1]:
            continue
        # 重複をなくす
        if aspect_word.count([opinion["@target"]]) > 1:
            continue
        aspect_detail = {
            'select_idx': list(map(lambda x: x - 1, aspect_from_to_index[index][:2])),
            'word_range': [int(opinion['@from']), int(opinion['@to'])],
            'polarity_pair': [""] * 2,
        }
        aspect = {
            'term': [opinion['@target']], 'from': aspect_from_to_index[index][0],
            'to': aspect_from_to_index[index][1], 'polarity': opinion['@polarity'],
        }
        index += 1
        if aspect and aspect_detail:
            # assert
            if max(aspect_detail['word_range']) < len(sentence['text']):
                aspects.append(aspect)
                aspect_details.append(aspect_detail)
    if split_sentence and aspects and aspect_details:
        if len(aspects) <= 1:
            return None
        data['token'] = split_sentence
        data['aspects'] = aspects
        data['aa_choice'] = aspect_details
    return data


def xml_to_json(file_name):
    with open(file_name, 'r', encoding='utf-8') as fp:
        # xml読み込み
        xml_data = fp.read()

    # xml → dict
    dict_data = xmltodict.parse(xml_data)
    json_data = []
    for token in dict_data["Reviews"]["Review"]:
        flag = False
        for sentence in token["sentences"]["sentence"]:
            if type(sentence) is not dict:
                flag = True
                data = sentence_parse(token["sentences"]["sentence"])
            else:
                data = sentence_parse(sentence)
            if data:
                json_data.append(data)
            if flag:
                break
    return json_data


def clear_json_data(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)


def xml_parse(json_file_name, xml_file_name):
    with open(json_file_name, 'w', encoding='utf-8') as f:
        json_data = xml_to_json(xml_file_name)
        json.dump(json_data, f, indent=4)
    parse_tree.preprocess_file(json_file_name)


def main(json_file_name, xml_file_name):
    xml_parse(json_file_name, xml_file_name)
    clear_json_data(json_file_name)


if __name__ == '__main__':
    en_dataset = [EN_TRAIN_XML, EN_TEST_XML, EN_TEST_XML]
    sp_dataset = [SP_TRAIN_XML, SP_TEST_XML, SP_TEST_XML]
    fr_dataset = [FR_TRAIN_XML, FR_TEST_XML, FR_TEST_XML]
    ru_dataset = [RU_TRAIN_XML, RU_TEST_XML, RU_TEST_XML]
    tu_dataset = [TU_TRAIN_XML, TU_TEST_XML, TU_TEST_XML]
    dataset = [en_dataset, sp_dataset, fr_dataset, ru_dataset, tu_dataset]
    data_dir = 'data'
    """
    for lang_path, lang in zip(dataset, ['en', 'sp', 'fr', 'ru', 'tu']):
        for xml_file_name, file_type in zip(lang_path, ['train', 'valid', 'test']):
            json_file_name = data_dir + '/' + lang + '/restaurant/' + file_type + '_con_new.json'
            main(json_file_name, xml_file_name)
    """
    main('data/en/restaurant/train_con_new.json', en_dataset[0])
