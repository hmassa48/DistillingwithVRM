from utils import utils
import torch
from torch.autograd import Variable


def train(model, optimizer, loss_fn, acc_fn, dataloader, use_gpu, epoch, writer,
          mixup=False, alpha=1.0, cutmix=False, cutmix_prob=0.5, beta=1.0):

    model.train()

    losses = utils.AverageMeter()
    accuracies = utils.AverageMeter()
    epoch_steps = len(dataloader)

    for i, (train_batch, label_batch) in enumerate(dataloader):
        niter = (epoch - 1)*epoch_steps + i
        if use_gpu:
            train_batch, label_batch = train_batch.cuda(), label_batch.cuda()

        if mixup:
            train_batch, label_batch_a, label_batch_b, lam = utils.mixup_data(
                train_batch, label_batch, alpha, use_gpu)
            train_batch, label_batch_a, label_batch_b = map(
                Variable, (train_batch, label_batch_a, label_batch_b))

            output_batch = model(train_batch)
            loss = utils.mixed_loss_fn(
                loss_fn, output_batch, label_batch_a, label_batch_b, lam)
            losses.update(loss.item())
            writer.add_scalar('data/stepwise_lambda', lam, niter)

        elif cutmix:
            train_batch, label_batch_a, label_batch_b, lam = utils.cutmix_data(
                train_batch, label_batch, beta, cutmix_prob, use_gpu)
            train_batch, label_batch_a, label_batch_b = map(
                Variable, (train_batch, label_batch_a, label_batch_b))

            output_batch = model(train_batch)
            loss = utils.mixed_loss_fn(
                loss_fn, output_batch, label_batch_a, label_batch_b, lam)
            losses.update(loss.item())
            writer.add_scalar('data/stepwise_lambda', lam, niter)

        else:
            # To set grad to zero on these
            train_batch, label_batch = map(
                Variable, (train_batch, label_batch))
            output_batch = model(train_batch)

            loss = loss_fn(output_batch, label_batch)
            acc, _, _, _ = utils.find_metrics(output_batch, label_batch, use_gpu)

            losses.update(loss.item())
            accuracies.update(acc)
            writer.add_scalar(
                'data/stepwise_training_accuracy', accuracies.val, niter)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        print(("Step: {}, Current Loss: {}, RunningLoss: {}").format(
            i, loss, losses.avg))
        writer.add_scalar('data/stepwise_training_loss', losses.val, niter)



    writer.add_scalar('data/training_loss', losses.avg, epoch)
    if not (mixup or cutmix):
        writer.add_scalar('data/training_accuracy', accuracies.avg, epoch)

    return losses.avg


def validate(model, loss_fn, acc_fn, dataloader, use_gpu, epoch, writer):

    losses = utils.AverageMeter()
    accuracies = utils.AverageMeter()
    precisions = utils.AverageMeter()
    recalls = utils.AverageMeter()

    model.eval()

    for i, (train_batch, label_batch) in enumerate(dataloader):
        if use_gpu:
            train_batch, label_batch = train_batch.cuda(), label_batch.cuda()

        with torch.no_grad():
            train_batch, label_batch = Variable(
                train_batch), Variable(label_batch)
            output_batch = model(train_batch)

            loss = loss_fn(output_batch, label_batch)

            acc, prec, rec, _ = utils.find_metrics(output_batch, label_batch, use_gpu)

            losses.update(loss.item())
            accuracies.update(acc)
            precisions.update(prec)
            recalls.update(rec)

            print(("Step: {}, Current Loss: {}, RunningLoss: {}").format(
                i, loss, losses.avg))
        


    writer.add_scalar('data/val_loss', losses.avg, epoch)
    writer.add_scalar('data/val_accuracy', accuracies.avg, epoch)
    writer.add_scalar('data/val_precision', precisions.avg, epoch)
    writer.add_scalar('data/val_recall', recalls.avg, epoch)

    return losses.avg
