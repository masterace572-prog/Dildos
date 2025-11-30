#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <errno.h>
#include <stdatomic.h>
#include <signal.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sched.h>

#define PAYLOAD_SIZE 1024
#define STATS_INTERVAL 1
#define BURST_SIZE 10  // Reduced for GitHub Actions safety

typedef struct {
    char target_ip[16];
    int target_port;
    int duration;
    int thread_id;
} thread_args;

_Atomic long total_sent = 0;
_Atomic long total_errors = 0;
volatile sig_atomic_t running = 1;

void int_handler(int sig) {
    running = 0;
}

void generate_payload(char *buffer, size_t size) {
    // Simple pattern-based payload (no /dev/urandom dependency)
    for (size_t i = 0; i < size; i++) {
        buffer[i] = (i % 256);
    }
}

void *send_payload(void *arg) {
    thread_args *args = (thread_args *)arg;
    char payload[PAYLOAD_SIZE];
    struct sockaddr_in target_addr;
    int sockfd;
    time_t start_time;

    printf("Thread %d started\n", args->thread_id);
    generate_payload(payload, PAYLOAD_SIZE);

    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Socket creation failed");
        return NULL;
    }

    // Set socket timeout to prevent hanging
    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 0;
    setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    memset(&target_addr, 0, sizeof(target_addr));
    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(args->target_port);
    
    if (inet_pton(AF_INET, args->target_ip, &target_addr.sin_addr) <= 0) {
        printf("Invalid IP: %s\n", args->target_ip);
        close(sockfd);
        return NULL;
    }

    start_time = time(NULL);
    
    printf("Thread %d: Starting send loop for %d seconds\n", 
           args->thread_id, args->duration);

    // Simple sendto loop (more compatible)
    while (running && (time(NULL) - start_time < args->duration)) {
        for (int i = 0; i < BURST_SIZE && running; i++) {
            ssize_t ret = sendto(sockfd, payload, PAYLOAD_SIZE, 0,
                               (struct sockaddr*)&target_addr, sizeof(target_addr));
            if (ret > 0) {
                atomic_fetch_add(&total_sent, 1);
            } else {
                atomic_fetch_add(&total_errors, 1);
                // Don't spam on errors
                usleep(1000);
            }
        }
        // Small delay to prevent overwhelming
        usleep(1000);
    }

    close(sockfd);
    printf("Thread %d finished\n", args->thread_id);
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 5) {
        printf("Usage: %s <IP> <PORT> <DURATION> <THREADS>\n", argv[0]);
        printf("Example: %s 127.0.0.1 80 10 2\n", argv[0]);
        return 1;
    }

    signal(SIGINT, int_handler);
    signal(SIGTERM, int_handler);

    char *target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int duration = atoi(argv[3]);
    int thread_count = atoi(argv[4]);

    // Safety limits for GitHub
    if (duration > 30) {
        printf("Warning: Duration limited to 30 seconds max\n");
        duration = 30;
    }
    if (thread_count > 4) {
        printf("Warning: Thread count limited to 4 max\n");
        thread_count = 4;
    }

    printf("UDP Test Tool - GitHub Safe Version\n");
    printf("Target: %s:%d\n", target_ip, target_port);
    printf("Duration: %d seconds\n", duration);
    printf("Threads: %d\n", thread_count);
    printf("Press Ctrl+C to stop early\n\n");

    pthread_t *threads = malloc(thread_count * sizeof(pthread_t));
    thread_args *args = malloc(thread_count * sizeof(thread_args));
    
    if (!threads || !args) {
        perror("Memory allocation failed");
        return 1;
    }

    // Create threads
    for (int i = 0; i < thread_count; i++) {
        strncpy(args[i].target_ip, target_ip, 15);
        args[i].target_ip[15] = '\0';
        args[i].target_port = target_port;
        args[i].duration = duration;
        args[i].thread_id = i;

        if (pthread_create(&threads[i], NULL, send_payload, &args[i]) != 0) {
            perror("Thread creation failed");
            running = 0;
            break;
        }
    }

    // Stats display
    time_t start = time(NULL);
    while (running && (time(NULL) - start < duration)) {
        sleep(STATS_INTERVAL);
        int elapsed = (int)(time(NULL) - start);
        int remaining = duration - elapsed;
        if (remaining < 0) remaining = 0;
        
        long sent = atomic_load(&total_sent);
        long errors = atomic_load(&total_errors);
        
        printf("[%02d:%02d] Packets: %ld, Errors: %ld, PPS: %.1f\n",
               remaining / 60, remaining % 60,
               sent, errors, (double)sent / (elapsed + 1));
               
        if (elapsed >= duration) running = 0;
    }

    running = 0;
    printf("\nStopping... Please wait\n");

    // Wait for threads
    for (int i = 0; i < thread_count; i++) {
        if (threads[i]) {
            pthread_join(threads[i], NULL);
        }
    }

    long final_sent = atomic_load(&total_sent);
    long final_errors = atomic_load(&total_errors);
    
    printf("\n=== FINAL RESULTS ===\n");
    printf("Total packets sent: %ld\n", final_sent);
    printf("Total errors: %ld\n", final_errors);
    printf("Success rate: %.2f%%\n", 
           final_sent > 0 ? (100.0 * (final_sent - final_errors) / final_sent) : 0);
    printf("Average PPS: %.2f\n", (double)final_sent / duration);
    printf("Total data: %.2f MB\n", (double)(final_sent * PAYLOAD_SIZE) / (1024 * 1024));

    free(threads);
    free(args);
    return 0;
}
