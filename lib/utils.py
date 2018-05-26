import csv

def parse_rpc_names(csv_rpc_names):
    rpc_names = []

    with open(csv_rpc_names, 'r') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(spamreader, None) #skip the header
        for row in spamreader:
            if '-' in row[1]:
                rng = range(int(row[1].split('-')[0]),int(row[1].split('-')[1]))
            else:
                rng = [int(row[1])]

            if len(row[0]) != 0:
                name = row[0]
            else:
                name = row[2]

            rpc_names.append({
                "name": name,
                "range": rng,
            })

    return rpc_names
