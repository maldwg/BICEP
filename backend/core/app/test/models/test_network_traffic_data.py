# @pytest.mark.asyncio
# async def test_calculate_malicious_benign_counts_from_text_stream():
#     labels_file_path = open(f'{TESTS_BASE_DIR}/testfiles/sample_data.csv', 'r')
#     benign_count, malicious_count = await calculate_malicious_benign_counts_from_text_stream(labels_file_path)
#     assert (benign_count, malicious_count) == (899,100)


# @pytest.mark.asyncio
# async def test_get_positives_and_negatives_from_dataset(sample_dataset, sample_alerts):
#     TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS = get_positives_and_negatives_from_dataset(sample_dataset, sample_alerts)
#     assert (TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS) == (9,6,893,91,0,15)




# # Test for get_column_ids
# @pytest.mark.asyncio
# async def test_get_column_ids():
#     header = ["Time", "Source IP", "Source Port", "Destination", "Destination Port", "Label"]
#     result_related_headers = get_column_ids(header)

#     expected_related_headers = (
#         5,  # Label column
#         0,  # Timestamp column
#         1,  # Source IP column
#         2,  # Source Port column
#         3,  # Destination IP column
#         4   # Destination Port column
#     )

#     header = ["Unknown", "Unrelated", "Time"]
#     result_unrelated_headers = get_column_ids(header)

#     expected_unrelated_headers = (
#         None,  # Label column
#         2,     # Timestamp column
#         None,  # Source IP column
#         None,  # Source Port column
#         None,  # Destination IP column
#         None   # Destination Port column
#     )
#     assert (expected_related_headers, expected_unrelated_headers) == (result_related_headers, result_unrelated_headers)

# @pytest.mark.asyncio
# async def test_get_item_counts_of_dict():
#     test_dict = {
#         "a": [1, 2, 3],
#         "b": [4, 5],
#         "c": []
#     }
#     result_five_element_dict = get_item_counts_of_dict(test_dict)

#     empty_dict = {}
#     result_empty_dict = get_item_counts_of_dict(empty_dict)

#     single_item_dict = {"a": [1]}
#     result_single_dict = get_item_counts_of_dict(single_item_dict)

#     assert (5, 1, 0) == (result_five_element_dict, result_single_dict, result_empty_dict)