import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.StringTokenizer;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.input.FileSplit;
import org.apache.hadoop.mapreduce.lib.input.TextInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

public class WordCounter {
	/**
	 * This class counts the occurrences of each word in a set of text files,
	 * excluding common stop words. It outputs the word along with the file name
	 * and the line numbers where the word appears.
	 */
	public static class WordCounterMapper extends Mapper<Object, Text, Text, Text> {
		private Text keyInfo   = new Text();
		private Text valueInfo = new Text();
		private String currentFile = "";
		private int rowCount = 0;
		private List<String> stopWords;

		@Override
		protected void setup(Context context) {
			// Load stop words from a resource file
			InputStream is = this.getClass().getResourceAsStream("/stopwords.txt");
			stopWords = new ArrayList<>();
			try (BufferedReader br = new BufferedReader(new InputStreamReader(is))) {
				String line;
				while ((line = br.readLine()) != null) {
					// Add each stop word to the list, trimming whitespace
					stopWords.add(line.trim());
				}
			} catch (IOException ex) {
				ex.printStackTrace();
			}
		}

		@Override
		public void map(Object key, Text value, Context context)
				throws IOException, InterruptedException {
			// Get the file name from the input split
			FileSplit split = (FileSplit) context.getInputSplit();
			String filename = split.getPath().getName();

			StringTokenizer lines = new StringTokenizer(value.toString(), "\n");
			while (lines.hasMoreTokens()) {
				// Check if the current file is the same as the previous one
				if (filename.equals(currentFile)) {
					rowCount++;
				} else {
					currentFile = filename;
					rowCount = 1;
				}

				String line = lines.nextToken();
				StringTokenizer words = new StringTokenizer(
						line,
						"\"',.()?![]#$*-=;:_+/\\<>@%& «»—"
				);

				while (words.hasMoreTokens()) {
					// Convert word to lowercase and check against stop words
					String word = words.nextToken().toLowerCase();
					if (!stopWords.contains(word)) {
						// Create the key and value for output
						keyInfo.set(word + ";" + filename);
						valueInfo.set(Integer.toString(rowCount));
						context.write(keyInfo, valueInfo);
					}
				}
			}
		}
	}

	/**
	 * Combiner class to aggregate the line numbers for each word in a file.
	 * This reduces the amount of data sent to the reducer.
	 */
	public static class WordCounterCombiner extends Reducer<Text, Text, Text, Text> {
		private Text valueInfo = new Text();

		@Override
		protected void reduce(Text key, Iterable<Text> values, Context context)
				throws IOException, InterruptedException {
			// Combine the line numbers for each word in a file
			StringBuilder lineNumbers = new StringBuilder();
			for (Text value : values) {
				lineNumbers.append(value.toString()).append(", ");
			}

			if (lineNumbers.length() >= 2) {
				lineNumbers.setLength(lineNumbers.length() - 2);
			}

			String[] parts = key.toString().split(";");
			String word = parts[0];
			String filename = parts[1];

			// Create the value in the format (filename, lineNumbers)
			valueInfo.set("(" + filename + ", " + lineNumbers + ")");
			key.set(word);
			context.write(key, valueInfo);
		}
	}

	/**
	 * Reducer class to aggregate the results from the combiner.
	 * It combines the line numbers for each word across all files.
	 */
	public static class WordCounterReducer extends Reducer<Text, Text, Text, Text> {
		private Text valueInfo = new Text();

		@Override
		protected void reduce(Text key, Iterable<Text> values, Context context)
				throws IOException, InterruptedException {
			// Aggregate the line numbers for each word across all files
			Map<String, List<String>> fileToLines = new HashMap<>();

			for (Text value : values) {
				// Parse the value in the format (filename, lineNumbers)
				String s = value.toString().trim();
				if (s.startsWith("(") && s.endsWith(")")) {
					s = s.substring(1, s.length() - 1).trim();
				}

				// Split the string into filename and line numbers
				String[] parts = s.split(",", 2);
				String filename = parts[0].trim();
				String rest = (parts.length > 1) ? parts[1].trim() : "";

				String[] nums = rest.split(",");
				List<String> list = fileToLines.computeIfAbsent(filename, k -> new ArrayList<>());
				for (String num : nums) {
					// Trim whitespace and add to the list if not empty
					String trimmed = num.trim();
					if (!trimmed.isEmpty()) {
						list.add(trimmed);
					}
				}
			}

			// Prepare the output in the format (filename, lineNumbers)
			StringBuilder fileList = new StringBuilder();
			for (Map.Entry<String, List<String>> entry : fileToLines.entrySet()) {
				// Join the line numbers for each file
				String filename = entry.getKey();
				List<String> lines = entry.getValue();
				StringBuilder joinedNums = new StringBuilder();
				for (int i = 0; i < lines.size(); i++) {
					// Append line numbers, separating them with commas
					joinedNums.append(lines.get(i));
					if (i < lines.size() - 1) {
						joinedNums.append(", ");
					}
				}
				fileList
						.append("(")
						.append(filename)
						.append(", ")
						.append(joinedNums)
						.append(") ");
			}

			if (fileList.length() >= 1) {
				fileList.setLength(fileList.length() - 1);
			}

			// Set the value to the aggregated file list
			valueInfo.set(fileList.toString());
			context.write(key, valueInfo);
		}
	}

	/**
	 * Main method to set up and run the Hadoop job.
	 * It configures the job with the mapper, combiner, and reducer classes,
	 * as well as the input and output formats.
	 *
	 * @param args Command line arguments: input path and output path
	 */
	public static void main(String[] args) throws Exception {
		Configuration conf = new Configuration();
		Job job = Job.getInstance(conf, "Word Counter");

		// Set the job's JAR by class, mapper, combiner, and reducer classes
		job.setJarByClass(WordCounter.class);
		job.setMapperClass(WordCounterMapper.class);
		job.setCombinerClass(WordCounterCombiner.class);
		job.setReducerClass(WordCounterReducer.class);
		job.setOutputKeyClass(Text.class);
		job.setOutputValueClass(Text.class);
		job.setInputFormatClass(TextInputFormat.class);

		// Set the input and output paths from command line arguments
		FileInputFormat.addInputPath(job, new Path(args[0]));
		FileOutputFormat.setOutputPath(job, new Path(args[1]));

		System.exit(job.waitForCompletion(true) ? 0 : 1);
	}
}
