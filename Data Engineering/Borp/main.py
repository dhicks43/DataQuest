import io

class Pipeline:
    def __init__(self):
        self.tasks = []
        self.header = [
            'ip', 'time_local', 'request_type',
            'request_path', 'status', 'bytes_sent',
            'http_referrer', 'http_user_agent'
        ]
        
    def task(self, depends_on=None):
        idx = 0
        if depends_on:
            idx = self.tasks.index(depends_on) + 1
        def inner(f):
            self.tasks.insert(idx, f)
            return f
        return inner
    
    def run(self, log):
        for i in self.tasks:
            log = i(log)

@pipeline.task()
def parse_log(log):
    for line in log:
        split_line = line.split()
        remote_addr = split_line[0]
        time_local = parse_time(split_line[3] + " " + split_line[4])
        request_type = strip_quotes(split_line[5])
        request_path = split_line[6]
        status = split_line[8]
        body_bytes_sent = split_line[9]
        http_referrer = strip_quotes(split_line[10])
        http_user_agent = strip_quotes(" ".join(split_line[11:]))
        yield (
            remote_addr, time_local, request_type, request_path,
            status, body_bytes_sent, http_referrer, http_user_agent
        )

pipeline = Pipeline()

@pipeline.task(depends_on=parse_log)
def build_csv(lines, header=pipeline.header, file=io.StringIO()):
    if header:
        lines = itertools.chain([header], lines)
    writer = csv.writer(file, delimiter=',')
    writer.writerows(lines)
    file.seek(0)
    return file
    
@pipeline.task(depends_on=build_csv)
def count_unique_request(csv_file):
    reader = csv.reader(csv_file)
    header = next(reader)
    idx = header.index('request_type')

    uniques = {}
    for line in reader:

        if not uniques.get(line[idx]):
            uniques[line[idx]] = 0
        uniques[line[idx]] += 1
    return ((k, v) for k,v in uniques.items())
    

log = open('example_log.txt')

summarize_csv = pipeline.run(log)
print(summarize_csv.readlines())