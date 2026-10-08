package org.mdp.kafka.cli;

import java.time.Duration;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.Properties;
import java.util.UUID;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.mdp.kafka.def.KafkaConstants;


public class BurstDetector {

    public static final int X = 50;
    public static final long Y_SECONDS = 50;

    public static void main(String[] args) {

        if(args.length!=1){
			System.err.println("Usage: BurstDetector <inputTopic>");
			return;
		}
  
        String inputTopic = args[0];

        Properties props = KafkaConstants.PROPS;
        // randomise consumer ID so messages cannot be read by another consumer
		//   (or at least it's more likely that a meteor wipes out life on Earth)
        
        props.put(ConsumerConfig.GROUP_ID_CONFIG, UUID.randomUUID().toString());


        KafkaConsumer<String, String> consumer = new KafkaConsumer<String, String>(props);
        consumer.subscribe(Arrays.asList(inputTopic));

        LinkedList<ConsumerRecord<String, String>> queue = new LinkedList<>();

        boolean eventActive = false;
        int eventId = 0;
        long yMs = 1000 * Y_SECONDS;

        try {
            while (true) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(10));
                for (ConsumerRecord<String, String> record : records) {
                    queue.add(record);
                    if(queue.size() < X) {
                        continue;
                    }
                    else if(queue.size() > X){
                        queue.removeFirst();
                    }
                    ConsumerRecord<String, String> fst = queue.getFirst();
                    ConsumerRecord<String, String> lst = queue.getLast();
                    long diff = lst.timestamp() - fst.timestamp();    
                    if (!eventActive && diff <= yMs) {
                        eventActive = true;
                        eventId++;
                        System.out.printf("Burst %d started at %d with value \"%s\"\n", eventId, fst.timestamp(), fst.value());
                    }
                    else if (eventActive && diff >= 2 * yMs) {
                        eventActive = false;
                        System.out.printf("Burst %d ended at %d with value \"%s\"\n", eventId, lst.timestamp(), lst.value());
                    }

                }
            }
        } finally {
            consumer.close();
        }


    }
}
