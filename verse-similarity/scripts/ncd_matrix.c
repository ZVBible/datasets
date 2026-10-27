/*
 * ncd_matrix.c — all-pairs gzip compressed lengths for verse NCD.
 *
 * Input : texts.txt  — one normalized verse per line (N lines)
 * Output: clen.u16   — C(x_i) for each verse (gzip-9 length, uint16 LE)
 *         pair.u16   — N*N row-major matrix, M[i][j] = C(x_i "\n" x_j)
 *                      (both concatenation orders; diagonal = C(x_i "\n" x_i))
 *         done.u8    — per-row completion flags (checkpoint / resume)
 *
 * Compression is real gzip (deflateInit2 windowBits=31, level 9, memLevel 8,
 * Z_DEFAULT_STRATEGY), identical in size to `gzip -9` / Node zlib.gzipSync
 * level 9 on the same bytes. NCD is derived later from these lengths.
 *
 * Build: gcc -O3 -march=native -pthread ncd_matrix.c -lz -o ncd_matrix
 * Run  : ./ncd_matrix texts.txt OUTDIR [threads]
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <stdatomic.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <zlib.h>

static char **txt; static int *tlen; static int N;
static uint16_t *clen;
static int fd_pair, fd_done;
static uint8_t *done;
static atomic_int next_row;
static atomic_long rows_done;
static long rows_todo;
static double t0;

static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}

static int gz_len(z_stream *zs, const unsigned char *a, int la, unsigned char *out, int outcap){
  deflateReset(zs);
  zs->next_in=(unsigned char*)a; zs->avail_in=la;
  zs->next_out=out; zs->avail_out=outcap;
  int r=deflate(zs,Z_FINISH);
  if(r!=Z_STREAM_END){fprintf(stderr,"deflate error %d\n",r);exit(2);}
  return outcap - zs->avail_out;
}

static void *worker(void *arg){
  (void)arg;
  z_stream zs; memset(&zs,0,sizeof zs);
  if(deflateInit2(&zs,9,Z_DEFLATED,31,8,Z_DEFAULT_STRATEGY)!=Z_OK) exit(3);
  int maxlen=0; for(int i=0;i<N;i++) if(tlen[i]>maxlen) maxlen=tlen[i];
  unsigned char *buf=malloc(2*maxlen+2), *out=malloc(4*maxlen+256);
  uint16_t *row=malloc(sizeof(uint16_t)*N);
  for(;;){
    int i=atomic_fetch_add(&next_row,1);
    if(i>=N) break;
    if(done[i]) continue;
    memcpy(buf,txt[i],tlen[i]); buf[tlen[i]]='\n';
    unsigned char *tail=buf+tlen[i]+1;
    for(int j=0;j<N;j++){
      memcpy(tail,txt[j],tlen[j]);
      row[j]=(uint16_t)gz_len(&zs,buf,tlen[i]+1+tlen[j],out,4*maxlen+256);
    }
    if(pwrite(fd_pair,row,sizeof(uint16_t)*N,(off_t)i*N*sizeof(uint16_t))!=(ssize_t)(sizeof(uint16_t)*N)){perror("pwrite");exit(4);}
    uint8_t one=1; done[i]=1;
    if(pwrite(fd_done,&one,1,i)!=1){perror("pwrite done");exit(4);}
    long d=atomic_fetch_add(&rows_done,1)+1;
    if(d%200==0||d==rows_todo){
      double el=now()-t0;
      fprintf(stderr,"rows %ld/%ld  %.1fs elapsed  eta %.0fs  (%.3f us wall per compression)\n",
        d,rows_todo,el,el/d*(rows_todo-d),el/((double)d*N)*1e6);
    }
  }
  deflateEnd(&zs); free(buf); free(out); free(row);
  return NULL;
}

int main(int argc,char**argv){
  if(argc<3){fprintf(stderr,"usage: %s texts.txt OUTDIR [threads]\n",argv[0]);return 1;}
  int nth=argc>3?atoi(argv[3]):(int)sysconf(_SC_NPROCESSORS_ONLN);
  FILE *f=fopen(argv[1],"rb"); if(!f){perror("texts");return 1;}
  fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET);
  char *all=malloc(sz+1); if(fread(all,1,sz,f)!=(size_t)sz) return 1; all[sz]=0; fclose(f);
  int cap=40000; txt=malloc(sizeof(char*)*cap); tlen=malloc(sizeof(int)*cap);
  for(char *p=all;*p;){char *e=strchr(p,'\n'); if(!e) e=p+strlen(p); txt[N]=p; tlen[N]=(int)(e-p); N++; if(!*e) break; *e=0; p=e+1;}
  fprintf(stderr,"N=%d verses, %d threads\n",N,nth);
  char path[4096];
  /* single-verse lengths */
  clen=malloc(sizeof(uint16_t)*N);
  { z_stream zs; memset(&zs,0,sizeof zs); deflateInit2(&zs,9,Z_DEFLATED,31,8,Z_DEFAULT_STRATEGY);
    unsigned char out[8192];
    for(int i=0;i<N;i++) clen[i]=(uint16_t)gz_len(&zs,(unsigned char*)txt[i],tlen[i],out,sizeof out);
    deflateEnd(&zs);
    snprintf(path,sizeof path,"%s/clen.u16",argv[2]); FILE *o=fopen(path,"wb"); fwrite(clen,2,N,o); fclose(o); }
  snprintf(path,sizeof path,"%s/pair.u16",argv[2]);
  fd_pair=open(path,O_RDWR|O_CREAT,0644); if(fd_pair<0){perror("pair");return 1;}
  if(ftruncate(fd_pair,(off_t)N*N*2)){perror("ftruncate");return 1;}
  snprintf(path,sizeof path,"%s/done.u8",argv[2]);
  fd_done=open(path,O_RDWR|O_CREAT,0644);
  done=calloc(N,1);
  { ssize_t r=pread(fd_done,done,N,0); if(r<N){ memset(done+(r>0?r:0),0,N-(r>0?r:0)); if(ftruncate(fd_done,N)){} } }
  for(int i=0;i<N;i++) if(!done[i]) rows_todo++;
  fprintf(stderr,"rows remaining: %ld\n",rows_todo);
  t0=now();
  pthread_t th[256]; for(int t=0;t<nth;t++) pthread_create(&th[t],NULL,worker,NULL);
  for(int t=0;t<nth;t++) pthread_join(th[t],NULL);
  fsync(fd_pair); close(fd_pair); close(fd_done);
  fprintf(stderr,"DONE in %.1fs\n",now()-t0);
  return 0;
}
