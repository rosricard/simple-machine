# station IDs are ints, treat them as opaque hashable values - don't assume anything about their range... that sounds like a key to a linked list (ie hashmap key)

# input is a list of ints [] and the number of stations, k
# find the number of stations and return them in descending order of most visited
# output is a sorted list of kth most visited stations

# brute force: Could potentially solve this by having a 2D array (instantiate new) and loop through the original array twice and record a new value as the first index and the second value as the number of occurances  O(n^2+M). Use the list sort function at the end (which i believe is O(n)

# the best pattern match for this problem is the count (frequecy) archetype
# there's a count portion and then a sort portion. Sorting we could use the built in list sort algorithm, which is 

def sort_most_visited(log : list, target : int) -> list[int]:
    counted_and_sorted = []
    counts = {} # declare as dictionary so we can use the station id as the key and the value will increment up as we count
    #loop through list, check if the value exists in the key and then add to the value count
    for c in log: 
        counts[c] = counts.get(c, 0) + 1

    # so now that we've counted the visits per station, we need to pick the kth most visited and order them into a list of descending order
    # suggest converting the dict to a list and then using the list sort function

    #in this case, the key is the station id and the value is the number of times it was visited. We want to publish the key and we want to sort by the value
    print(counts.items())
    sort_by_value = dict(sorted(counts.items(), key = lambda item: item[1], reverse = True))
    print(sort_by_value)

    # now we need to convert the keys to a list
    for station_id, count in sort_by_value.items():
        print(f"station id: {station_id} | count {count}")
        counted_and_sorted.append(station_id)
    
    return counted_and_sorted[:target]


if __name__ == "__main__":
    log = [1, 1, 1, 2, 2, 3]
    k = 2
    print(sort_most_visited(log, k))